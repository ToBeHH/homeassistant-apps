"""Offline place search.

Two kinds of index, each its own SQLite file in <data_path>/geocode, replaced
as a whole when finished:

- geonames.sqlite: places, mountains, rivers and so on plus postal codes, from
  the GeoNames dumps (CC BY 4.0).
- map-<label>.sqlite: streets and points of interest found in that map region.

Rows are stored most important first, so a search can stop after the first few
hundred hits of a common word without ranking millions of them.
"""

import datetime
import io
import json
import logging
import math
import os
import re
import shutil
import sqlite3
import time
import unicodedata
import urllib.request
import zipfile

from . import USER_AGENT, fetch, maps, pmread
from .status import now

log = logging.getLogger(__name__)

GEONAMES_URL = "https://download.geonames.org/export/dump/allCountries.zip"
POSTAL_URL = "https://download.geonames.org/export/zip/allCountries.zip"
GB = 1000**3
MIN_MAP_ZOOM = 13  # names of streets and POIs only exist further in
KINDS = {"A": "region", "H": "water", "L": "area", "P": "place", "R": "road",
         "S": "site", "T": "mountain", "U": "undersea", "V": "forest"}
WEIGHT = {"P": 10_000, "A": 5_000, "T": 100, "H": 100, "L": 50, "V": 50, "R": 10, "S": 5, "U": 1}
POI_LAYERS = {"roads", "pois", "water"}
# A street is one row per area of about 2 km, not one per tile it crosses.
CELL = 0.02

_SCHEMA = """
CREATE TABLE places(
    id INTEGER PRIMARY KEY, name TEXT, alt TEXT, kind TEXT, near TEXT, country TEXT,
    lat REAL, lon REAL);
"""
_FTS = """
CREATE VIRTUAL TABLE fts USING fts5(
    name, alt, near, content='places', content_rowid='id',
    tokenize="unicode61 remove_diacritics 2", prefix='2 3');
INSERT INTO fts(rowid, name, alt, near) SELECT id, name, alt, near FROM places;
INSERT INTO fts(fts) VALUES('optimize');
"""


def folder(data_path):
    return os.path.join(data_path, "geocode")


def _open_build(path):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.executescript(
        "CREATE TABLE raw(score INT, name TEXT, alt TEXT, kind TEXT, near TEXT, country TEXT,"
        " lat REAL, lon REAL, cell TEXT);" + _SCHEMA
    )
    return db


def _finish_build(db, tmp, dest, extra=""):
    db.executescript(
        "INSERT INTO places(name, alt, kind, near, country, lat, lon)"
        " SELECT name, alt, kind, near, country, lat, lon FROM raw ORDER BY score DESC;"
        "DROP TABLE raw;" + _FTS + extra
    )
    db.execute("VACUUM")
    db.close()
    os.replace(tmp, dest)


def _rows(archive_path, member):
    with zipfile.ZipFile(archive_path) as z:
        with z.open(member) as f:
            for line in io.TextIOWrapper(f, encoding="utf-8", newline="\n"):
                yield line.rstrip("\n").split("\t")


def build_geonames(places_zip, postal_zip, dest):
    tmp = dest + ".build"
    db = _open_build(tmp)
    insert = "INSERT INTO raw VALUES(?,?,?,?,?,?,?,?,NULL)"
    batch = []

    def add(row):
        batch.append(row)
        if len(batch) >= 50_000:
            db.executemany(insert, batch)
            batch.clear()

    for r in _rows(places_zip, "allCountries.txt"):
        if len(r) < 15:
            continue
        cls = r[6]
        population = int(r[14]) if r[14].isdigit() else 0
        alt = " ".join(a for a in r[3].split(",") if a and not a.startswith("http"))[:1000]
        add((WEIGHT.get(cls, 1) + population, r[1], alt, KINDS.get(cls, "site"), "", r[8],
             float(r[4]), float(r[5])))
    for r in _rows(postal_zip, "allCountries.txt"):
        if len(r) < 11 or not r[9] or not r[10]:
            continue
        add((50, r[1], "", "postcode", r[2], r[0], float(r[9]), float(r[10])))
    db.executemany(insert, batch)
    _finish_build(db, tmp, dest,
                  "CREATE INDEX towns ON places(lat, lon) WHERE kind = 'place';")


class Towns:
    """Nearest town for a coordinate, from geonames.sqlite if there is one."""

    def __init__(self, path):
        self.db = _connect(path) if os.path.exists(path) else None
        self.memo = {}

    def near(self, lat, lon):
        if self.db is None:
            return "", ""
        cell = (round(lat / CELL), round(lon / CELL))
        if cell not in self.memo:
            if len(self.memo) > 200_000:
                self.memo.clear()
            self.memo[cell] = self._lookup(lat, lon)
        return self.memo[cell]

    def _lookup(self, lat, lon):
        d = 0.25
        rows = self.db.execute(
            "SELECT name, country, lat, lon, id FROM places WHERE kind = 'place'"
            " AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
            (lat - d, lat + d, lon - 2 * d, lon + 2 * d),
        ).fetchall()
        if not rows:
            return "", ""
        scale = math.cos(math.radians(lat)) ** 2
        nearest = min(rows, key=lambda r: (r[2] - lat) ** 2 + scale * (r[3] - lon) ** 2)
        # The nearest place is often a quarter; people search for the city around it.
        # Rows are stored by importance, so the lowest ID is the biggest town here.
        biggest = min(rows, key=lambda r: r[4])
        names = dict.fromkeys((nearest[0], biggest[0]))
        return ", ".join(names), nearest[1]

    def close(self):
        if self.db is not None:
            self.db.close()


def build_map_index(archive_path, dest, towns, progress=None):
    tmp = dest + ".build"
    db = _open_build(tmp)
    db.execute("CREATE UNIQUE INDEX once ON raw(cell)")
    archive = pmread.Archive(archive_path)
    zoom = archive.max_zoom
    insert = "INSERT OR IGNORE INTO raw VALUES(?,?,?,?,?,?,?,?,?)"
    batch = []
    done = 0
    last = time.monotonic()
    score = {"roads": 2, "water": 1}
    for x, y, data, stored in archive.tiles(zoom):
        for layer, props, lon, lat in pmread.named_features(data, zoom, x, y, POI_LAYERS):
            name = props["name"]
            kind = "road" if layer == "roads" else props.get("kind") or layer
            cell = f"{name}|{kind}|{round(lat / CELL)}|{round(lon / CELL)}"
            alt = " ".join(v for k, v in props.items() if k.startswith("name:") and v != name)
            town, country = towns.near(lat, lon)
            batch.append((score.get(layer, 0), name, alt, kind, town, country, lat, lon, cell))
        done += stored
        if len(batch) >= 20_000:
            db.executemany(insert, batch)
            batch.clear()
        if progress and time.monotonic() - last > 5:
            progress(done)
            last = time.monotonic()
    db.executemany(insert, batch)
    archive.close()
    db.execute("DROP INDEX once")
    _finish_build(db, tmp, dest)
    return done


# --- Searching ----------------------------------------------------------------


def _connect(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)


def _plain(text):
    """Lower case without diacritics, as the search index sees text."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _closeness(name, wanted):
    plain = _plain(name)
    if plain == wanted:
        return 0
    return 1 if plain.startswith(wanted) else 2


def search(query, data_path, limit=20):
    """Best matches over all indexes: exact names first, then names starting with
    the query, then the rest; within those by importance."""
    tokens = re.findall(r"\w+", query.lower())
    if not tokens or len("".join(tokens)) < 2:
        return []
    directory = folder(data_path)
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    # geonames first: on equal footing a town beats a bus stop of that name.
    files = sorted((n for n in names if n.endswith(".sqlite")), key=lambda n: n != "geonames.sqlite")
    words = " ".join(f'"{t}"' for t in tokens) + "*"
    # The name first, because alternate names of big places would drown it otherwise.
    matches = (f"name : ({words})", words)
    wanted = _plain(query.strip())
    hits = []
    seen = set()
    for order, name in enumerate(files):
        db = _connect(os.path.join(directory, name))
        try:
            for match in matches:
                rows = db.execute(
                    "SELECT p.name, p.kind, p.near, p.country, p.lat, p.lon FROM fts"
                    " JOIN places p ON p.id = fts.rowid WHERE fts MATCH ? LIMIT 200",
                    (match,),
                ).fetchall()
                for i, r in enumerate(rows):
                    # A street crosses many index cells, but is one street per town.
                    where = (r[2], r[3]) if r[1] == "road" and r[2] else (round(r[4], 2), round(r[5], 2))
                    key = (r[0].lower(), r[1], where)
                    if key in seen:
                        continue
                    seen.add(key)
                    in_name = match is matches[0]
                    hits.append(((_closeness(r[0], wanted), r[1] != "place", not in_name, order, i), r))
        except sqlite3.Error as err:
            log.warning("Search in %s failed: %s", name, err)
        finally:
            db.close()
    hits.sort(key=lambda h: h[0])
    return [
        dict(zip(("name", "kind", "near", "country", "lat", "lon"), r))
        for _, r in hits[:limit]
    ]


# --- Keeping the indexes up to date --------------------------------------------


def _read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def _remote_size(url, timeout=60):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.headers.get("Content-Length") or 0)


def _reserve_ok(directory, need, key, status):
    free = shutil.disk_usage(directory).free
    if free >= need + 2 * GB:
        return True
    msg = f"needs about {need / GB:.1f} GB plus reserve, {free / GB:.1f} GB free"
    log.warning("Skipping place search index: %s", msg)
    status.item(key, kind="search", state="no_space", message=msg)
    return False


def geonames_stale(state, update_days, today=None):
    built = state.get("geonames")
    if not built:
        return True
    if not update_days:
        return False
    today = today or datetime.date.today()
    return (today - datetime.date.fromisoformat(built)).days >= update_days


def update(opts, status, window, urls=(GEONAMES_URL, POSTAL_URL)):
    """Bring the search indexes in line. True when nothing failed."""
    directory = folder(opts.data_path)
    os.makedirs(directory, exist_ok=True)
    state_path = os.path.join(directory, "state.json")
    state = _read_state(state_path)
    ok = True
    if geonames_stale(state, opts.map_update_days):
        try:
            _update_geonames(directory, urls, opts, status, window)
            state["geonames"] = datetime.date.today().isoformat()
            _write_state(state_path, state)
        except Exception as err:  # network, disk or broken dump: retry later
            log.error("GeoNames index failed: %s", err)
            status.item("search:geonames", kind="search", state="error", message=str(err))
            ok = False
    else:
        status.item("search:geonames", kind="search", title="Places (GeoNames)",
                    file="geonames.sqlite", state="current")

    maps_dir = os.path.join(opts.data_path, "maps")
    regions = maps.read_index(maps_dir)["regions"]
    done = state.setdefault("regions", {})
    for label, region in sorted(regions.items(), key=lambda kv: kv[1].get("size", 0)):
        if region.get("maxzoom", 0) < MIN_MAP_ZOOM:
            continue
        key = f"search:{label}"
        title = f"Streets and places: {region.get('title', label)}"
        file = f"map-{label}.sqlite"
        if done.get(label) == region.get("build") and os.path.exists(os.path.join(directory, file)):
            status.item(key, kind="search", title=title, file=file, state="current")
            continue
        size = region.get("size", 0)
        if not _reserve_ok(directory, size // 5, key, status):
            ok = False
            continue
        log.info("Building the search index for map %s; this can take hours", label)
        status.set(state="downloading", message=f"search index for {label}")
        status.item(key, kind="search", title=title, file=file, state="downloading", size=size, done=0)
        started = time.monotonic()
        try:
            build_map_index_from(maps_dir, region, directory, file, status, key)
        except Exception as err:
            log.error("Search index for %s failed: %s", label, err)
            status.item(key, state="error", message=str(err))
            ok = False
            continue
        done[label] = region.get("build")
        _write_state(state_path, state)
        status.item(key, state="current", done=size)
        log.info("Search index for %s finished in %.0f min", label, (time.monotonic() - started) / 60)

    # Indexes of maps that are gone.
    for name in os.listdir(directory):
        m = re.match(r"map-(.+)\.sqlite(\.build)?$", name)
        if m and (m.group(2) or m.group(1) not in regions):
            os.remove(os.path.join(directory, name))
    return ok


def build_map_index_from(maps_dir, region, directory, file, status, key):
    towns = Towns(os.path.join(directory, "geonames.sqlite"))
    try:
        build_map_index(
            os.path.join(maps_dir, region["file"]),
            os.path.join(directory, file),
            towns,
            progress=lambda done: status.item(key, done=done),
        )
    finally:
        towns.close()


def _update_geonames(directory, urls, opts, status, window):
    key = "search:geonames"
    title = "Places (GeoNames)"
    places_url, postal_url = urls
    sizes = [_remote_size(places_url), _remote_size(postal_url)]
    # Text unpacked plus search index, measured at about ten times the download.
    if not _reserve_ok(directory, sum(sizes) * 10, key, status):
        raise OSError("not enough space")
    paths = []
    for url, size, name in zip(urls, sizes, ("geonames-places.zip", "geonames-postal.zip")):
        while not window.is_open():
            time.sleep(min(window.seconds_until_open(), 3600))
        status.set(state="downloading", message=title)
        status.item(key, kind="search", title=title, file="geonames.sqlite",
                    state="downloading", size=size, done=0)
        path = os.path.join(directory, name)
        paths.append(path)
        if os.path.exists(path) and os.path.getsize(path) == size:
            continue
        fetch.download([url], path, size, {}, limit_kbps=opts.download_limit,
                       progress=lambda done: status.item(key, done=done))
    log.info("Building the place search index from GeoNames")
    status.set(state="downloading", message="place search index")
    build_geonames(paths[0], paths[1], os.path.join(directory, "geonames.sqlite"))
    for path in paths:
        os.remove(path)
    log.info("Place search index finished at %s", now())
    status.item(key, state="current")
