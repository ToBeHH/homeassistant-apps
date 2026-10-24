"""Offline maps: regions cut out of the Protomaps planet build.

`pmtiles extract` reads only the needed byte ranges of the remote planet
file. Each region ends up as <data_path>/maps/<label>.pmtiles; index.json next
to them tells the map viewer (and the next run) what is there.
"""

import dataclasses
import datetime
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.request

from . import USER_AGENT

log = logging.getLogger(__name__)

REGIONS_FILE = os.path.join(os.path.dirname(__file__), "regions.json")
BUILDS_URL = "https://build-metadata.protomaps.dev/builds.json"
BUILD_URL = "https://build.protomaps.com/{key}"
PMTILES = os.environ.get("OKDL_PMTILES", "pmtiles")
INDEX = "index.json"
PART = ".part"
MAX_ZOOM = 15  # the planet build goes to 15
CUSTOM_ZOOM = 14

_LABEL = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


class ExtractError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Region:
    label: str
    bbox: tuple  # min_lon, min_lat, max_lon, max_lat
    maxzoom: int
    title: str = ""

    @property
    def file(self):
        return f"{self.label}.pmtiles"

    @property
    def bbox_arg(self):
        return ",".join(f"{v:g}" for v in self.bbox)


def load_regions(path=REGIONS_FILE):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        k: Region(k, tuple(v["bbox"]), int(v["maxzoom"]), v.get("title", k))
        for k, v in data.items()
        if not k.startswith("_")
    }


def _zoom(text):
    z = int(text)
    if not 0 <= z <= MAX_ZOOM:
        raise ValueError(f"zoom {z} is outside 0–{MAX_ZOOM}")
    return z


def _bbox(text):
    parts = [float(p) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("a bbox needs four numbers")
    w, s, e, n = parts
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ValueError("bbox must be min_lon,min_lat,max_lon,max_lat")
    return tuple(parts)


def parse(spec, regions):
    """'germany', 'germany:12' or 'home=9.7,53.4,10.3,53.7[:15]' -> Region."""
    spec = spec.strip()
    if "=" in spec:
        label, _, rest = spec.partition("=")
        bbox, _, zoom = rest.partition(":")
        label = label.strip().lower()
        if not _LABEL.match(label):
            raise ValueError(f"'{label}' is not a valid region name (a-z, 0-9, - and _)")
        return Region(
            label, _bbox(bbox), _zoom(zoom) if zoom else CUSTOM_ZOOM, label
        )
    name, _, zoom = spec.partition(":")
    name = name.strip().lower()
    if name not in regions:
        known = ", ".join(sorted(regions))
        raise ValueError(f"unknown region '{name}' (known: {known}, or name=bbox)")
    r = regions[name]
    return dataclasses.replace(r, maxzoom=_zoom(zoom)) if zoom else r


def wanted(specs, regions=None):
    """Option list -> ([Region], problems). Later duplicates of a label lose."""
    regions = load_regions() if regions is None else regions
    out, problems, seen = [], [], set()
    for spec in specs:
        try:
            r = parse(spec, regions)
        except ValueError as err:
            problems.append(f"map region '{spec}': {err}")
            continue
        if r.label in seen:
            problems.append(f"map region '{r.label}' is listed twice")
            continue
        seen.add(r.label)
        out.append(r)
    return out, problems


# --- Planet builds ------------------------------------------------------------


def load_builds(url=BUILDS_URL, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def latest_build(builds):
    keys = sorted(b["key"] for b in builds if str(b.get("key", "")).endswith(".pmtiles"))
    if not keys:
        raise ValueError("no Protomaps builds listed")
    return keys[-1]


def build_date(key):
    return datetime.datetime.strptime(key[:8], "%Y%m%d").date()


# --- Index of what is on disk -------------------------------------------------


def read_index(maps_dir):
    try:
        with open(os.path.join(maps_dir, INDEX), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data.get("regions"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"regions": {}}


def write_index(maps_dir, index):
    path = os.path.join(maps_dir, INDEX)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def index_entry(region, build_key, size):
    return {
        "file": region.file,
        "title": region.title,
        "bbox": list(region.bbox),
        "maxzoom": region.maxzoom,
        "build": build_key,
        "size": size,
        "selected": True,
    }


def part_files(maps_dir):
    try:
        return sorted(n for n in os.listdir(maps_dir) if n.endswith(".pmtiles" + PART))
    except FileNotFoundError:
        return []


@dataclasses.dataclass
class Plan:
    current: list = dataclasses.field(default_factory=list)  # [Region]
    extract: list = dataclasses.field(default_factory=list)  # [(Region, reason)]
    prune: list = dataclasses.field(default_factory=list)  # [label]
    keep: list = dataclasses.field(default_factory=list)  # [label]


def make_plan(wanted_regions, index, maps_dir, build_key, update_days, prune, today=None):
    """Decide what to extract. A region is redone when its file is missing,
    its bbox or zoom changed, or its build is update_days old (0 = never)
    and a newer build exists."""
    today = today or datetime.date.today()
    have_all = index.get("regions", {})
    p = Plan()
    for r in wanted_regions:
        have = have_all.get(r.label)
        if not have or not os.path.exists(os.path.join(maps_dir, have.get("file", ""))):
            p.extract.append((r, "missing"))
        elif have.get("bbox") != list(r.bbox) or have.get("maxzoom") != r.maxzoom:
            p.extract.append((r, "area or zoom changed"))
        elif (
            update_days
            and have.get("build") != build_key
            and (today - build_date(have["build"])).days >= update_days
        ):
            p.extract.append((r, f"older than {update_days} days"))
        else:
            p.current.append(r)
    labels = {r.label for r in wanted_regions}
    for label in sorted(set(have_all) - labels):
        (p.prune if prune else p.keep).append(label)
    return p


# --- The pmtiles binary -------------------------------------------------------

_SIZE = re.compile(r"archive size of ([\d.]+)\s*([kKMGTP]?B)")
_UNITS = {"B": 1, "kB": 10**3, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12, "PB": 10**15}


def parse_dry_run(output):
    m = _SIZE.search(output)
    if not m:
        return None
    return int(float(m.group(1)) * _UNITS[m.group(2)])


class Extractor:
    def __init__(self, command=(PMTILES,), threads=4, poll=5):
        self.command = list(command)
        self.threads = threads
        self.poll = poll  # seconds between progress reports

    def _args(self, url, region, out):
        return self.command + [
            "extract",
            url,
            out,
            f"--bbox={region.bbox_arg}",
            f"--maxzoom={region.maxzoom}",
            f"--download-threads={self.threads}",
        ]

    def dry_run(self, url, region):
        """Expected archive size in bytes, or None if it can't be told."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                res = subprocess.run(
                    self._args(url, region, os.path.join(tmp, region.file)) + ["--dry-run"],
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
        except (OSError, subprocess.TimeoutExpired) as err:
            log.warning("Size estimate for %s failed: %s", region.label, err)
            return None
        size = parse_dry_run(res.stdout + res.stderr)
        if res.returncode != 0 or size is None:
            log.warning("Size estimate for %s failed: %s", region.label, res.stderr.strip()[-300:])
        return size

    def extract(self, url, region, part, progress=None):
        if os.path.exists(part):
            os.remove(part)
        proc = subprocess.Popen(
            self._args(url, region, part) + ["--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        while proc.poll() is None:
            time.sleep(self.poll)
            if progress and os.path.exists(part):
                progress(os.path.getsize(part))
        _, err = proc.communicate()
        if proc.returncode != 0:
            raise ExtractError(f"pmtiles extract failed ({proc.returncode}): {err.strip()[-300:]}")
        res = subprocess.run(self.command + ["verify", part], capture_output=True, text=True)
        if res.returncode != 0:
            raise ExtractError(f"pmtiles verify failed: {(res.stdout + res.stderr).strip()[-300:]}")
