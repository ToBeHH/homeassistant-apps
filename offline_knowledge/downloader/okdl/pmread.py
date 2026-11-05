"""Reading PMTiles v3 archives and Mapbox vector tiles, without dependencies.

Only what the place search needs: walk the tiles of one zoom level and get the
named features with one coordinate each.
"""

import gzip
import math
import os
import struct

HEADER_LEN = 127
GZIP = 2


def _varint(buf, i):
    result = shift = 0
    while True:
        byte = buf[i]
        i += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return result, i


def tile_id_to_zxy(tile_id):
    """The Hilbert curve numbering of the PMTiles spec, backwards."""
    z = 0
    start = 0
    while tile_id >= start + 4**z:
        start += 4**z
        z += 1
    d = tile_id - start
    x = y = 0
    s = 1
    while s < (1 << z):
        rx = 1 & (d // 2)
        ry = 1 & (d ^ rx)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        d //= 4
        s *= 2
    return z, x, y


def zoom_range(z):
    """First tile ID of zoom z and first one after it."""
    first = (4**z - 1) // 3
    return first, first + 4**z


def parse_directory(buf):
    """[(tile_id, run_length, offset, length)]; run_length 0 means a leaf."""
    count, i = _varint(buf, 0)
    ids, runs, lengths = [], [], []
    tile_id = 0
    for _ in range(count):
        delta, i = _varint(buf, i)
        tile_id += delta
        ids.append(tile_id)
    for _ in range(count):
        v, i = _varint(buf, i)
        runs.append(v)
    for _ in range(count):
        v, i = _varint(buf, i)
        lengths.append(v)
    entries = []
    previous_end = 0
    for k in range(count):
        v, i = _varint(buf, i)
        offset = previous_end if v == 0 and k > 0 else v - 1
        entries.append((ids[k], runs[k], offset, lengths[k]))
        previous_end = offset + lengths[k]
    return entries


class Archive:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY)
        header = os.pread(self.fd, HEADER_LEN, 0)
        if header[:7] != b"PMTiles" or header[7] != 3:
            raise ValueError(f"{path} is not a PMTiles v3 archive")
        o = struct.unpack("<QQQQQQQQ", header[8:72])
        self.root = (o[0], o[1])
        self.leaf_offset = o[4]
        self.data_offset = o[6]
        self.data_length = o[7]
        self.internal_gzip = header[97] == GZIP
        self.tile_gzip = header[98] == GZIP
        self.max_zoom = header[101]

    def close(self):
        os.close(self.fd)

    def _directory(self, offset, length):
        buf = os.pread(self.fd, length, offset)
        return parse_directory(gzip.decompress(buf) if self.internal_gzip else buf)

    def _entries(self, entries, first, end):
        for k, (tile_id, run, offset, length) in enumerate(entries):
            # A leaf or a run reaches up to the next entry at most.
            upto = entries[k + 1][0] if k + 1 < len(entries) else end
            if tile_id >= end or upto <= first:
                continue
            if run == 0:
                yield from self._entries(
                    self._directory(self.leaf_offset + offset, length), first, end
                )
            elif tile_id >= first:
                yield tile_id, run, offset, length

    def tiles(self, zoom):
        """(x, y, tile bytes, stored length) per stored tile of a zoom level.
        Runs (identical tiles, mostly open sea) count once."""
        first, end = zoom_range(zoom)
        for tile_id, _run, offset, length in self._entries(self._directory(*self.root), first, end):
            data = os.pread(self.fd, length, self.data_offset + offset)
            if self.tile_gzip:
                data = gzip.decompress(data)
            _, x, y = tile_id_to_zxy(tile_id)
            yield x, y, data, length


def _fields(buf):
    i = 0
    n = len(buf)
    while i < n:
        key, i = _varint(buf, i)
        wire = key & 7
        if wire == 0:
            value, i = _varint(buf, i)
        elif wire == 2:
            length, i = _varint(buf, i)
            value = buf[i : i + length]
            i += length
        elif wire == 1:
            value = buf[i : i + 8]
            i += 8
        elif wire == 5:
            value = buf[i : i + 4]
            i += 4
        else:
            raise ValueError(f"unknown protobuf wire type {wire}")
        yield key >> 3, value


def _packed(buf):
    out = []
    i = 0
    while i < len(buf):
        v, i = _varint(buf, i)
        out.append(v)
    return out


def named_features(data, z, x, y, layers, wanted_keys=("name", "name:de", "name:en", "kind")):
    """(layer, {key: text}, lon, lat) for named features in the given layers."""
    wanted = set(wanted_keys)
    n = 2**z
    for field, layer in _fields(data):
        if field != 3:
            continue
        name = None
        features, keys, values = [], [], []
        extent = 4096
        for f, v in _fields(layer):
            if f == 1:
                name = v.decode()
            elif f == 2:
                features.append(v)
            elif f == 3:
                keys.append(v.decode())
            elif f == 4:
                values.append(v)
            elif f == 5:
                extent = v
        if name not in layers or "name" not in keys:
            continue
        name_key = keys.index("name")
        for feature in features:
            tags = geometry = None
            for f, v in _fields(feature):
                if f == 2:
                    tags = _packed(v)
                elif f == 4:
                    geometry = v
            if not tags or not geometry or name_key not in tags[::2]:
                continue
            props = {}
            for k, val in zip(tags[::2], tags[1::2]):
                if keys[k] in wanted:
                    for vf, text in _fields(values[val]):
                        if vf == 1:
                            props[keys[k]] = text.decode()
            if "name" not in props:
                continue
            _, i = _varint(geometry, 0)  # the MoveTo command
            dx, i = _varint(geometry, i)
            dy, i = _varint(geometry, i)
            px = (dx >> 1) ^ -(dx & 1)
            py = (dy >> 1) ^ -(dy & 1)
            lon = (x + px / extent) / n * 360 - 180
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
            yield name, props, lon, lat
