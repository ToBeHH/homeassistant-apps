"""python3 -m kbsync – keep the Kolibri channels imported."""

import argparse
import json
import logging
import sys
import time

from . import sync

CHECK_EVERY = 24 * 3600
RETRY_AFTER = 3600


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kbsync", description=__doc__)
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--state", default="/data/channel_sync.json")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    log = logging.getLogger("kbsync")
    while True:
        try:
            with open(args.options, encoding="utf-8") as f:
                options = json.load(f)
            ok = sync.run_once(options, args.state)
        except Exception as err:  # keep the service alive, report, retry
            log.exception("Channel sync failed: %s", err)
            ok = False
        time.sleep(CHECK_EVERY if ok else RETRY_AFTER)


if __name__ == "__main__":
    sys.exit(main())
