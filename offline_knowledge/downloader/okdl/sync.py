"""One sync run: bring <data_path>/zim in line with the options."""

import json
import logging
import os
import shutil
import time

from . import catalog, fetch, metalink, plan, selection
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

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))


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


def reserve(total_bytes):
    return max(MIN_RESERVE, total_bytes // 50)


def _remove(zim_dir, names, why):
    for name in names:
        path = os.path.join(zim_dir, name)
        try:
            os.remove(path)
            log.info("Removed %s (%s)", name, why)
        except FileNotFoundError:
            pass
        except OSError as err:
            log.warning("Could not remove %s: %s", name, err)


def run(opts, status, catalog_cache, catalog_url=catalog.CATALOG_URL):
    """True when no download failed. Unknown names don't count: retrying
    won't fix a typo in the options."""
    status.reset_items()
    problem = storage_problem(opts.data_path)
    if problem:
        log.warning("%s. Nothing will be downloaded.", problem)
        status.set(state="waiting_for_storage", message=problem)
        return False

    window = fetch.Window(opts.download_window)
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

    status.set(state="checking", message="reading the Kiwix catalog", last_check=now())
    try:
        entries = catalog.load(catalog_cache, url=catalog_url)
    except Exception as err:
        log.error("Kiwix catalog not available: %s", err)
        status.set(state="error", message=f"catalog not available: {err}")
        return False

    p = plan.make(
        names,
        entries,
        plan.local_files(zim_dir),
        plan.part_files(zim_dir),
        prune=opts.prune,
    )
    for name in p.unknown:
        log.warning("'%s' is not in the Kiwix catalog, skipped", name)
        status.item(name, state="unknown")
    for e in p.current:
        status.item(e.key, state="current", file=e.filename, size=e.size)
    for name in p.keep:
        log.info("%s is no longer selected; kept (prune is off)", name)

    _remove(zim_dir, p.obsolete, "older edition")
    _remove(zim_dir, p.stale_parts, "unfinished download no longer needed")
    _remove(zim_dir, p.prune, "no longer selected")

    for e in p.downloads:
        status.item(e.key, state="queued", file=e.filename, size=e.size, done=0)
    total = sum(e.size for e in p.downloads)
    if not p.downloads:
        log.info("All %d sources are up to date", len(p.current))
        status.set(state="idle", message="up to date", last_success=now())
        return True

    free = shutil.disk_usage(zim_dir).free
    log.info(
        "%d downloads, %.1f GB; %.1f GB free", len(p.downloads), total / GB, free / GB
    )
    if free < total + reserve(total):
        log.warning(
            "Not enough space for all downloads (%.1f GB needed incl. reserve, "
            "%.1f GB free); downloading what fits",
            (total + reserve(total)) / GB,
            free / GB,
        )

    ok = True
    for e in p.downloads:
        if not _download_one(e, zim_dir, p.replaces.get(e.filename, []), opts, window, status):
            ok = False
    status.set(
        state="idle",
        message="up to date" if ok and not p.unknown else "finished with problems",
        **({"last_success": now()} if ok else {}),
    )
    return ok


def _download_one(e, zim_dir, replaces, opts, window, status):
    dest = os.path.join(zim_dir, e.filename)
    part = dest + plan.PART
    have = os.path.getsize(part) if os.path.exists(part) else 0
    need = max(0, e.size - have)
    free = shutil.disk_usage(zim_dir).free
    if free < need + reserve(e.size):
        msg = f"needs {need / GB:.1f} GB plus reserve, {free / GB:.1f} GB free"
        log.warning("Skipping %s: %s", e.filename, msg)
        status.item(e.key, state="no_space", message=msg)
        return False

    while not window.is_open():
        wait = window.seconds_until_open()
        log.info("Outside download window %s, waiting %.0f min", window.spec, wait / 60)
        status.set(state="waiting_for_window", message=window.spec)
        time.sleep(min(wait, 3600))

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

    log.info("Downloading %s (%.2f GB)%s", e.filename, size / GB, " – resuming" if have else "")
    status.set(state="downloading", message=e.filename)
    status.item(e.key, state="downloading", size=size, done=have)

    def progress(done):
        status.item(e.key, done=done)
        log.info("%s: %.0f %%", e.filename, 100 * done / size if size else 0)

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
