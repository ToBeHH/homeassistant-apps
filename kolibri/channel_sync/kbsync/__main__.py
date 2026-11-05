"""python3 -m kbsync – keep the Kolibri channels imported."""

import argparse
import json
import logging
import os
import sys
import time

from . import sync

CHECK_EVERY = 24 * 3600
RETRY_AFTER = 3600


def wait_for_trigger(path, seconds, poll=5):
    """Sleep up to seconds; True as soon as a check was requested."""
    deadline = time.monotonic() + seconds
    while True:
        if os.path.exists(path):
            os.remove(path)
            return True
        left = deadline - time.monotonic()
        if left <= 0:
            return False
        time.sleep(min(poll, left))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kbsync", description=__doc__)
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--state", default="/data/channel_sync.json")
    ap.add_argument("--trigger", default="/run/kbsync.trigger")
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
        wait_for_trigger(args.trigger, CHECK_EVERY if ok else RETRY_AFTER)


if __name__ == "__main__":
    sys.exit(main())
