"""python3 -m okdl [--once] – keep the ZIM library in sync."""

import argparse
import datetime
import logging
import os
import sys
import time

from . import catalog, maps, sync
from .status import Status

CHECK_EVERY = 24 * 3600
RETRY_AFTER = 3600


def main(argv=None):
    ap = argparse.ArgumentParser(prog="okdl", description=__doc__)
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--state-dir", default="/data/downloader")
    ap.add_argument("--catalog-url", default=catalog.CATALOG_URL)
    ap.add_argument("--builds-url", default=maps.BUILDS_URL)
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

    while True:
        try:
            opts = sync.Options.load(args.options)
            ok = sync.run(opts, status, sources)
        except Exception as err:  # keep the service alive, report, retry
            log.exception("Sync failed: %s", err)
            status.set(state="error", message=str(err))
            ok = False
        if args.once:
            return 0 if ok else 1
        wait = CHECK_EVERY if ok else RETRY_AFTER
        log.info("Next check in %.0f h", wait / 3600)
        nxt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=wait)
        status.set(next_check=nxt.isoformat(timespec="seconds"))
        time.sleep(wait)


if __name__ == "__main__":
    sys.exit(main())
