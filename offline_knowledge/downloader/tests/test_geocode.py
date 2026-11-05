import gzip
import math
import os
import tempfile
import unittest
import zipfile

from okdl import geocode, pmread


def _varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def _field(n, payload):
    return _varint(n << 3 | 2) + _varint(len(payload)) + payload


def _num(n, v):
    return _varint(n << 3) + _varint(v)


def _zigzag(v):
    return (v << 1) ^ (v >> 31)


def tile(layers, z, x, y):
    """layers: {name: [(props, lon, lat)]}"""
    out = b""
    n = 2**z
    for name, feats in layers.items():
        keys, values, body = [], [], b""
        for props, lon, lat in feats:
            tags = []
            for k, v in props.items():
                keys.append(k) if k not in keys else None
                values.append(v) if v not in values else None
                tags += [keys.index(k), values.index(v)]
            px = round(((lon + 180) / 360 * n - x) * 4096)
            lat_rad = math.radians(lat)
            py = round(((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n - y) * 4096)
            geom = _varint(9) + _varint(_zigzag(px)) + _varint(_zigzag(py))
            body += _field(2, _field(2, b"".join(map(_varint, tags))) + _num(3, 1) + _field(4, geom))
        layer = _field(1, name.encode()) + body
        layer += b"".join(_field(3, k.encode()) for k in keys)
        layer += b"".join(_field(4, _field(1, v.encode())) for v in values)
        layer += _num(5, 4096) + _num(15, 2)
        out += _field(3, layer)
    return out


def zxy_to_id(z, x, y):
    first, _ = pmread.zoom_range(z)
    # Brute force is fine for the small coordinates of a test.
    for d in range(4**z):
        if pmread.tile_id_to_zxy(first + d) == (z, x, y):
            return first + d
    raise ValueError


def archive(path, tiles, zoom):
    """tiles: {(x, y): tile bytes}; a one-directory PMTiles v3 file."""
    entries = sorted((zxy_to_id(zoom, x, y), data) for (x, y), data in tiles.items())
    data = b""
    rows = []
    for tile_id, raw in entries:
        packed = gzip.compress(raw)
        rows.append((tile_id, len(data), len(packed)))
        data += packed
    d = _varint(len(rows))
    last = 0
    for tile_id, _, _ in rows:
        d += _varint(tile_id - last)
        last = tile_id
    d += b"".join(_varint(1) for _ in rows)
    d += b"".join(_varint(r[2]) for r in rows)
    d += b"".join(_varint(r[1] + 1) for r in rows)
    root = gzip.compress(d)
    header = b"PMTiles\x03"
    offsets = [127, len(root), 127 + len(root), 0, 127 + len(root), 0, 127 + len(root), len(data)]
    header += b"".join(v.to_bytes(8, "little") for v in offsets)
    header += bytes(24) + bytes([1, 2, 2, 1, 0, zoom]) + bytes(127)
    header = header[:127]
    with open(path, "wb") as f:
        f.write(header + root + data)


PLACE_ROW = "\t".join(
    ["2911298", "Hamburg", "Hamburg", "Hambourg,Amburgo,https://x", "53.55", "10.0", "P", "PPLA",
     "DE", "", "", "", "", "", "1739117", "", "", "", ""]
)
VILLAGE_ROW = "\t".join(
    ["1", "Hamburg", "Hamburg", "", "40.5", "-75.9", "P", "PPL", "US", "", "", "", "", "", "4289",
     "", "", "", ""]
)
RIVER_ROW = "\t".join(
    ["2", "Elbe", "Elbe", "Labe", "53.9", "9.0", "H", "STM", "DE", "", "", "", "", "", "0", "", "",
     "", ""]
)
POSTAL_ROW = "\t".join(
    ["DE", "20095", "Hamburg", "Hamburg", "HH", "", "", "", "", "53.55", "10.0", "4"]
)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = self.tmp.name
        self.dir = geocode.folder(self.data)
        os.makedirs(self.dir)
        self.geonames = os.path.join(self.dir, "geonames.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def zip(self, name, rows):
        path = os.path.join(self.data, name)
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("allCountries.txt", "\n".join(rows) + "\n")
        return path

    def build_geonames(self):
        geocode.build_geonames(
            self.zip("p.zip", [VILLAGE_ROW, RIVER_ROW, PLACE_ROW, "short\trow"]),
            self.zip("z.zip", [POSTAL_ROW]),
            self.geonames,
        )


class ReaderTest(Base):
    def test_hilbert_ids(self):
        self.assertEqual(pmread.tile_id_to_zxy(0), (0, 0, 0))
        self.assertEqual(pmread.tile_id_to_zxy(1), (1, 0, 0))
        self.assertEqual(pmread.tile_id_to_zxy(2), (1, 0, 1))
        self.assertEqual(pmread.tile_id_to_zxy(3), (1, 1, 1))
        self.assertEqual(pmread.tile_id_to_zxy(4), (1, 1, 0))
        # Every tile of a zoom level appears exactly once.
        first, end = pmread.zoom_range(3)
        self.assertEqual(len({pmread.tile_id_to_zxy(i) for i in range(first, end)}), 64)

    def test_named_features_and_position(self):
        z, x, y = 2, 2, 1
        raw = tile({"roads": [({"name": "Elbchaussee", "kind": "minor_road"}, 9.9, 53.5),
                              ({"kind": "path"}, 9.0, 53.0)],
                    "buildings": [({"name": "skipped"}, 9.0, 53.0)]}, z, x, y)
        found = list(pmread.named_features(raw, z, x, y, {"roads"}))
        self.assertEqual(len(found), 1)
        layer, props, lon, lat = found[0]
        self.assertEqual((layer, props["name"], props["kind"]), ("roads", "Elbchaussee", "minor_road"))
        self.assertAlmostEqual(lon, 9.9, places=1)
        self.assertAlmostEqual(lat, 53.5, places=1)

    def test_walks_only_the_wanted_zoom(self):
        path = os.path.join(self.data, "m.pmtiles")
        archive(path, {(0, 0): b"a", (1, 1): b"b"}, 1)
        a = pmread.Archive(path)
        self.assertEqual(a.max_zoom, 1)
        self.assertEqual(sorted((x, y, d) for x, y, d, _ in a.tiles(1)), [(0, 0, b"a"), (1, 1, b"b")])
        self.assertEqual(list(a.tiles(2)), [])
        a.close()

    def test_not_an_archive(self):
        path = os.path.join(self.data, "x")
        with open(path, "wb") as f:
            f.write(b"nope" * 100)
        with self.assertRaises(ValueError):
            pmread.Archive(path)


class SearchTest(Base):
    def setUp(self):
        super().setUp()
        self.build_geonames()

    def search(self, q, **kw):
        return geocode.search(q, self.data, **kw)

    def test_big_town_first(self):
        hits = self.search("Hamburg")
        self.assertEqual((hits[0]["country"], hits[0]["kind"]), ("DE", "place"))
        self.assertEqual(hits[1]["country"], "US")

    def test_alternate_names_prefix_diacritics_postcode(self):
        self.assertEqual(self.search("Amburgo")[0]["name"], "Hamburg")
        self.assertEqual(self.search("Hamb")[0]["name"], "Hamburg")
        self.assertEqual(self.search("HAMBÜRG")[0]["name"], "Hamburg")
        hit = self.search("20095")[0]
        self.assertEqual((hit["kind"], hit["near"]), ("postcode", "Hamburg"))
        self.assertEqual(self.search("Labe")[0]["kind"], "water")

    def test_typing_finds_the_name_before_alternate_names(self):
        self.assertEqual(self.search("Ham")[0]["name"], "Hamburg")
        self.assertEqual(self.search("el")[0]["name"], "Elbe")

    def test_quarter_and_city(self):
        town_rows = [
            PLACE_ROW,
            "\t".join(["3", "St. Pauli", "St. Pauli", "", "53.55", "9.96", "P", "PPLX", "DE", "", "",
                       "", "", "", "27000", "", "", "", ""]),
        ]
        geocode.build_geonames(self.zip("p2.zip", town_rows), self.zip("z2.zip", [POSTAL_ROW]), self.geonames)
        towns = geocode.Towns(self.geonames)
        self.assertEqual(towns.near(53.55, 9.961), ("St. Pauli, Hamburg", "DE"))
        towns.close()

    def test_harmless_input(self):
        for q in ("", " ", "a", '"', "*", 'x" OR "y', "AND", "(("):
            self.assertIsInstance(self.search(q), list)
        self.assertEqual(self.search("zzzzzz"), [])

    def test_no_index_no_results(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(geocode.search("Hamburg", d), [])

    def test_map_index_adds_streets_with_their_town(self):
        path = os.path.join(self.data, "m.pmtiles")
        # A small zoom stands in for 15; the coordinates only need a tile to live in.
        raw = tile({"roads": [({"name": "Rathausstraße", "kind": "minor_road"}, 9.99, 53.55),
                                    ({"name": "Rathausstraße", "kind": "minor_road"}, 9.99, 53.55)],
                          "pois": [({"name": "Rathaus", "kind": "townhall"}, 9.99, 53.55)]}, 2, 2, 1)
        archive(path, {(2, 1): raw}, 2)
        towns = geocode.Towns(self.geonames)
        geocode.build_map_index(path, os.path.join(self.dir, "map-t.sqlite"), towns)
        towns.close()
        hits = self.search("Rathausstraße")
        self.assertEqual(len(hits), 1)  # same street, same area: one row
        self.assertEqual((hits[0]["kind"], hits[0]["near"], hits[0]["country"]), ("road", "Hamburg", "DE"))
        # Street and town together find it too.
        self.assertEqual(self.search("Rathausstraße Hamburg")[0]["name"], "Rathausstraße")


class StateTest(unittest.TestCase):
    def test_stale(self):
        today = geocode.datetime.date(2026, 11, 5)
        self.assertTrue(geocode.geonames_stale({}, 30, today))
        self.assertFalse(geocode.geonames_stale({"geonames": "2026-10-10"}, 30, today))
        self.assertTrue(geocode.geonames_stale({"geonames": "2026-10-01"}, 30, today))
        self.assertFalse(geocode.geonames_stale({"geonames": "2020-01-01"}, 0, today))


if __name__ == "__main__":
    unittest.main()
