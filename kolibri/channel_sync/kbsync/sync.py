"""One sync run over all channels from the options."""

import json
import logging
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

STUDIO = "https://studio.learningequality.org"
GB = 1000**3
# Keep this much free on top of what a channel needs.
MIN_RESERVE = 2 * GB

_CHANNEL_ID = re.compile(r"^[0-9a-f]{32}$")


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


def lookup(channel_id, studio=STUDIO, timeout=60):
    """Published name, version and size of a channel, or None if unknown."""
    url = f"{studio}/api/public/v1/channels/lookup/{channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "kolibri-ha-app"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            found = json.load(resp)
    except urllib.error.HTTPError as err:
        err.close()
        if err.code == 404:
            return None
        raise
    return found[0] if found else None


def read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def needs_import(meta, have):
    return not have or not have.get("complete") or have.get("version") != meta.get("version")


def bytes_needed(meta, have):
    """Free space a channel needs. Started before: most of it is already there."""
    return 0 if have else int(meta.get("published_size") or 0)


def manage(*args):
    """Runs next to the live server, so it must leave the database setup alone."""
    return subprocess.run(["kolibri", "manage", "--skip-update", *args]).returncode


def import_channel(channel_id, run=manage):
    return (
        run("importchannel", "network", channel_id) == 0
        and run("importcontent", "network", channel_id) == 0
    )


def run_once(options, state_path, studio=STUDIO, run=manage):
    """True when no channel failed. Unknown IDs don't count: retrying won't
    fix a typo in the options."""
    problem = storage_problem((options.get("data_path") or "").strip())
    channels = options.get("channels") or []
    if not channels:
        return True
    if problem:
        log.warning("%s. Nothing will be downloaded.", problem)
        return False

    ok = True
    state = read_state(state_path)
    for channel_id in channels:
        channel_id = channel_id.strip().lower()
        if not _CHANNEL_ID.match(channel_id):
            log.warning("'%s' is not a channel ID (32 hexadecimal characters)", channel_id)
            continue
        have = state.get(channel_id)
        try:
            meta = lookup(channel_id, studio)
        except OSError as err:
            log.error("Kolibri Studio not available: %s", err)
            return False
        if meta is None:
            log.warning("Channel %s is not on Kolibri Studio, skipped", channel_id)
            continue
        name = meta.get("name", channel_id)
        if not needs_import(meta, have):
            log.info("%s is up to date", name)
            continue

        need = bytes_needed(meta, have)
        free = shutil.disk_usage(options["data_path"]).free
        if free < need + max(MIN_RESERVE, need // 50):
            log.warning(
                "Skipping %s: needs %.1f GB plus reserve, %.1f GB free",
                name, need / GB, free / GB,
            )
            ok = False
            continue

        log.info("Importing %s (%.1f GB)", name, int(meta.get("published_size") or 0) / GB)
        state[channel_id] = {"version": meta.get("version"), "complete": False}
        write_state(state_path, state)
        if import_channel(channel_id, run):
            state[channel_id]["complete"] = True
            write_state(state_path, state)
            log.info("Finished %s", name)
        else:
            log.error("Import of %s failed, trying again later", name)
            ok = False
    return ok
