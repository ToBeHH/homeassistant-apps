"""python3 -m okdl [--once] – keep the ZIM library and the maps in sync."""

import argparse
import datetime
import logging
import os
import sys
import time
import urllib.request

from . import catalog, control, maps, sync
from .status import Status

DAY = 24 * 3600
RETRY_AFTER = 3600
# Zimi notices new files only from its first folder check on, about 30 s after
# it started. Files that arrive earlier stay unseen until its next start.
LIBRARY_SETTLE = 60


def wait_for_library(url):
    while True:
        try:
            urllib.request.urlopen(url, timeout=5).close()
            break
        except OSError:
            time.sleep(5)
    time.sleep(LIBRARY_SETTLE)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="okdl", description=__doc__)
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--state-dir", default="/data/downloader")
    ap.add_argument("--catalog-url", default=catalog.CATALOG_URL)
    ap.add_argument("--builds-url", default=maps.BUILDS_URL)
    ap.add_argument("--token-file", default="/data/mcp_token")
    ap.add_argument("--wait-for", help="URL that must answer before the first run")
    ap.add_argument("--control-port", type=int, default=control.PORT)
    ap.add_argument("--once", action="store_true", help="one run, then exit")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    log = logging.getLogger("okdl")
    os.makedirs(args.state_dir, exist_ok=True)
    status = Status(os.path.join(args.state_dir, "status.json"))
    sources = sync.Sources(
        os.path.join(args.state_dir, "catalog.xml"),
        catalog_url=args.catalog_url,
        builds_url=args.builds_url,
    )
    if not args.once:
        # Up first: the start page needs it while the library is still loading.
        control.serve(args.state_dir, args.token_file, args.control_port)
    if args.wait_for:
        log.info("Waiting for the library server")
        wait_for_library(args.wait_for)

    while True:
        days = 1
        try:
            opts = sync.Options.load(args.options)
            days = opts.update_interval_days
            ok = sync.run(opts, status, sources)
        except Exception as err:  # keep the service alive, report, retry
            log.exception("Sync failed: %s", err)
            status.set(state="error", message=str(err))
            ok = False
        if args.once:
            return 0 if ok else 1
        wait = days * DAY if ok else RETRY_AFTER
        log.info("Next check in %.0f h", wait / 3600)
        nxt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=wait)
        status.set(next_check=nxt.isoformat(timespec="seconds"))
        control.wait_for_update(args.state_dir, wait)


if __name__ == "__main__":
    sys.exit(main())
