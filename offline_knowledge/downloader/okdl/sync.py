"""One sync run: bring <data_path>/zim and <data_path>/maps in line with the
options."""

import json
import logging
import os
import shutil
import time

from . import catalog, fetch, maps, metalink, plan, selection
from .status import now

log = logging.getLogger(__name__)

GB = 1000**3
# Keep this much free on top of what the downloads need.
MIN_RESERVE = 2 * GB


class Options:
    def __init__(self, raw):
        self.data_path = (raw.get("data_path") or "").strip()
        self.profile = raw.get("profile") or "slim"
        self.languages = list(raw.get("languages") or [])
        self.zim_sources = list(raw.get("zim_sources") or [])
        self.prune = bool(raw.get("prune", False))
        self.download_window = raw.get("download_window") or ""
        self.download_limit = int(raw.get("download_limit") or 0)
        self.map_regions = list(raw.get("map_regions") or [])
        self.map_update_days = int(raw.get("map_update_days") or 0)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))


class Sources:
    """Where catalogs and tools live; replaced in tests."""

    def __init__(
        self,
        catalog_cache,
        catalog_url=catalog.CATALOG_URL,
        builds_url=maps.BUILDS_URL,
        build_url=maps.BUILD_URL,
        extractor=None,
    ):
        self.catalog_cache = catalog_cache
        self.catalog_url = catalog_url
        self.builds_url = builds_url
        self.build_url = build_url
        self.extractor = extractor or maps.Extractor()


def storage_problem(data_path):
    """Why data_path can't be used, or None. Never creates data_path itself."""
    if not data_path:
        return "No storage location (data_path) configured"
    if not os.path.isabs(data_path):
        return f"Storage location '{data_path}' is not an absolute path"
    if not os.path.isdir(data_path):
        return f"Storage location '{data_path}' does not exist"
    if not os.access(data_path, os.W_OK):
        return f"Storage location '{data_path}' is not writable"
    return None


def storage_info(path):
    usage = shutil.disk_usage(path)
    return {"path": path, "free": usage.free, "total": usage.total}


def human(n):
    for unit, size in (("GB", GB), ("MB", 1000**2), ("kB", 1000)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} B"


def reserve(total_bytes):
    return max(MIN_RESERVE, total_bytes // 50)


def _remove(folder, names, why):
    for name in names:
        path = os.path.join(folder, name)
        try:
            os.remove(path)
            log.info("Removed %s (%s)", name, why)
        except FileNotFoundError:
            pass
        except OSError as err:
            log.warning("Could not remove %s: %s", name, err)


def _close(err):
    if hasattr(err, "close"):
        err.close()  # an HTTPError holds the response open


def _wait_for_window(window, status):
    while not window.is_open():
        wait = window.seconds_until_open()
        log.info("Outside download window %s, waiting %.0f min", window.spec, wait / 60)
        status.set(state="waiting_for_window", message=window.spec)
        time.sleep(min(wait, 3600))


def _has_space(folder, need, size, key, label, status):
    free = shutil.disk_usage(folder).free
    if free >= need + reserve(size):
        return True
    msg = f"needs {need / GB:.1f} GB plus reserve, {free / GB:.1f} GB free"
    log.warning("Skipping %s: %s", label, msg)
    status.item(key, state="no_space", message=msg)
    return False


def _progress(key, label, size, status):
    logged = [-1]

    def progress(done):
        status.item(key, done=done)
        # Log every 10 %, the status file gets every update.
        step = min(10, int(10 * done / size)) if size else 0
        if step > logged[0]:
            logged[0] = step
            log.info("%s: %d %%", label, step * 10)

    return progress


def run(opts, status, sources):
    """True when no download failed. Unknown names don't count: retrying
    won't fix a typo in the options."""
    status.reset_items()
    problem = storage_problem(opts.data_path)
    if problem:
        log.warning("%s. Nothing will be downloaded.", problem)
        status.set(state="waiting_for_storage", message=problem, storage=None)
        return False

    window = fetch.Window(opts.download_window)
    status.set(storage=storage_info(opts.data_path), last_check=now())

    ok = True
    jobs = []  # (size, label, callable -> bool)
    for part in (_zim_jobs, _map_jobs):
        part_ok, part_jobs = part(opts, status, sources, window)
        ok = ok and part_ok
        jobs.extend(part_jobs)

    if jobs:
        total = sum(size for size, _, _ in jobs)
        free = shutil.disk_usage(opts.data_path).free
        log.info("%d downloads, %s; %s free", len(jobs), human(total), human(free))
        if free < total + reserve(total):
            log.warning(
                "Not enough space for all downloads (%.1f GB needed incl. reserve, "
                "%.1f GB free); downloading what fits",
                (total + reserve(total)) / GB,
                free / GB,
            )
        # Smallest first: something useful arrives early, and a big file that
        # does not fit does not block the rest.
        for _, _, job in sorted(jobs, key=lambda j: (j[0], j[1])):
            if not job():
                ok = False
            status.set(storage=storage_info(opts.data_path))
    else:
        log.info("Everything is up to date")

    status.set(
        state="idle",
        message="up to date" if ok else "finished with problems",
        **({"last_success": now()} if ok else {}),
    )
    return ok


# --- ZIM files ----------------------------------------------------------------


def _zim_jobs(opts, status, sources, window):
    zim_dir = os.path.join(opts.data_path, "zim")
    os.makedirs(zim_dir, exist_ok=True)

    names, problems = selection.wanted(opts.profile, opts.languages, opts.zim_sources)
    for p in problems:
        log.warning("Option problem: %s", p)
    log.info(
        "Profile %s, languages %s: %d sources wanted",
        opts.profile,
        ", ".join(opts.languages) or "-",
        len(names),
    )
    if not names and not plan.local_files(zim_dir):
        return True, []

    status.set(state="checking", message="reading the Kiwix catalog")
    try:
        entries = catalog.load(sources.catalog_cache, url=sources.catalog_url)
    except Exception as err:
        _close(err)
        log.error("Kiwix catalog not available: %s", err)
        status.set(message=f"Kiwix catalog not available: {err}")
        return False, []

    p = plan.make(
        names,
        entries,
        plan.local_files(zim_dir),
        plan.part_files(zim_dir),
        prune=opts.prune,
    )
    for name in p.unknown:
        log.warning("'%s' is not in the Kiwix catalog, skipped", name)
        status.item(name, kind="zim", state="unknown")
    for e in p.current:
        status.item(e.key, kind="zim", title=e.title, state="current", file=e.filename, size=e.size)
    for name in p.keep:
        log.info("%s is no longer selected; kept (prune is off)", name)

    _remove(zim_dir, p.obsolete, "older edition")
    _remove(zim_dir, p.stale_parts, "unfinished download no longer needed")
    _remove(zim_dir, p.prune, "no longer selected")

    jobs = []
    for e in p.downloads:
        status.item(e.key, kind="zim", title=e.title, state="queued", file=e.filename, size=e.size, done=0)
        replaces = p.replaces.get(e.filename, [])
        jobs.append(
            (e.size, e.key, lambda e=e, r=replaces: _download_one(e, zim_dir, r, opts, window, status))
        )
    return True, jobs


def _download_one(e, zim_dir, replaces, opts, window, status):
    dest = os.path.join(zim_dir, e.filename)
    part = dest + plan.PART
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if not _has_space(zim_dir, max(0, e.size - have), e.size, e.key, e.filename, status):
        return False
    _wait_for_window(window, status)

    try:
        meta = metalink.load(e.meta4_url)
    except Exception as err:
        log.error("Metalink for %s not available: %s", e.filename, err)
        status.item(e.key, state="error", message=f"metalink: {err}")
        return False
    if meta.filename and meta.filename != e.filename:
        log.error("Metalink names %s, catalog %s; skipped", meta.filename, e.filename)
        status.item(e.key, state="error", message="metalink does not match catalog")
        return False
    urls = list(meta.urls)
    direct = e.meta4_url[: -len(".meta4")] if e.meta4_url.endswith(".meta4") else ""
    if direct and direct not in urls:
        urls.append(direct)
    size = meta.size or e.size

    log.info("Downloading %s (%s)%s", e.filename, human(size), " – resuming" if have else "")
    status.set(state="downloading", message=e.filename)
    status.item(e.key, state="downloading", size=size, done=have)
    progress = _progress(e.key, e.filename, size, status)

    while True:
        try:
            fetch.download(
                urls,
                dest,
                size,
                meta.hashes,
                window=window,
                limit_kbps=opts.download_limit,
                progress=progress,
            )
            break
        except fetch.OutsideWindow:
            wait = window.seconds_until_open()
            log.info("Download window closed, pausing %s for %.0f min", e.filename, wait / 60)
            status.item(e.key, state="paused")
            status.set(state="waiting_for_window", message=window.spec)
            time.sleep(max(60, min(wait, 3600)))
            status.item(e.key, state="downloading")
            status.set(state="downloading", message=e.filename)
        except fetch.DownloadError as err:
            log.error("Download of %s failed: %s", e.filename, err)
            status.item(e.key, state="error", message=str(err))
            return False

    log.info("Finished %s", e.filename)
    status.item(e.key, state="current", done=size)
    _remove(zim_dir, replaces, f"replaced by {e.filename}")
    return True


# --- Maps ---------------------------------------------------------------------


def _map_jobs(opts, status, sources, window):
    maps_dir = os.path.join(opts.data_path, "maps")
    os.makedirs(maps_dir, exist_ok=True)
    regions, problems = maps.wanted(opts.map_regions)
    for p in problems:
        log.warning("Option problem: %s", p)
    index = maps.read_index(maps_dir)
    if not regions and not index["regions"]:
        return True, []

    _remove(maps_dir, maps.part_files(maps_dir), "unfinished map extract")

    status.set(state="checking", message="reading the Protomaps build list")
    try:
        build_key = maps.latest_build(maps.load_builds(sources.builds_url))
    except Exception as err:
        _close(err)
        log.error("Protomaps build list not available: %s", err)
        status.set(message=f"Protomaps build list not available: {err}")
        for r in regions:
            if r.label in index["regions"]:
                status.item(f"map:{r.label}", kind="map", title=r.title, state="current")
        return False, []

    p = maps.make_plan(
        regions, index, maps_dir, build_key, opts.map_update_days, opts.prune
    )
    for label in p.prune:
        _remove(maps_dir, [index["regions"][label].get("file", f"{label}.pmtiles")], "no longer selected")
        index["regions"].pop(label, None)
    for label in p.keep:
        log.info("Map %s is no longer selected; kept (prune is off)", label)
        index["regions"][label]["selected"] = False
    for r in p.current:
        index["regions"][r.label]["selected"] = True
        have = index["regions"][r.label]
        status.item(
            f"map:{r.label}", kind="map", title=r.title, state="current",
            file=have.get("file"), size=have.get("size"),
        )
    maps.write_index(maps_dir, index)

    url = sources.build_url.format(key=build_key)
    jobs = []
    for r, reason in p.extract:
        key = f"map:{r.label}"
        status.item(key, kind="map", title=r.title, state="queued", file=r.file, done=0)
        log.info("Map %s: %s, estimating size", r.label, reason)
        size = sources.extractor.dry_run(url, r)
        if size:
            status.item(key, size=size)
        jobs.append(
            (size or 0, key, lambda r=r, s=size: _extract_one(r, s, url, build_key, maps_dir, window, status, sources))
        )
    return True, jobs


def _extract_one(region, size, url, build_key, maps_dir, window, status, sources):
    key = f"map:{region.label}"
    # The old file stays until the new one is complete, so the full size is needed.
    if not _has_space(maps_dir, size or 0, size or 0, key, f"map {region.label}", status):
        return False
    _wait_for_window(window, status)

    part = os.path.join(maps_dir, region.file + maps.PART)
    log.info("Extracting map %s (%s)", region.label, human(size) if size else "size unknown")
    status.set(state="downloading", message=f"map {region.label}")
    status.item(key, state="downloading", done=0)
    try:
        sources.extractor.extract(url, region, part, progress=_progress(key, f"map {region.label}", size, status))
    except (OSError, maps.ExtractError) as err:
        log.error("Map %s failed: %s", region.label, err)
        status.item(key, state="error", message=str(err))
        _remove(maps_dir, [region.file + maps.PART], "failed extract")
        return False

    final = os.path.getsize(part)
    os.replace(part, os.path.join(maps_dir, region.file))
    index = maps.read_index(maps_dir)
    index["regions"][region.label] = maps.index_entry(region, build_key, final)
    maps.write_index(maps_dir, index)
    log.info("Finished map %s", region.label)
    status.item(key, state="current", size=final, done=final)
    return True
