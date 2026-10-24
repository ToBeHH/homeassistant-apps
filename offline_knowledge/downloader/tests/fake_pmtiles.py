#!/usr/bin/env python3
"""Stands in for the pmtiles binary in tests.

extract <in> <out> ... [--dry-run]  writes 1000 bytes per zoom level
verify <file>                       ok unless the file is empty
FAKE_PMTILES_FAIL=1                 makes extract fail
"""

import os
import sys

args = sys.argv[1:]
cmd = args[0]
if cmd == "extract":
    out = args[2]
    zoom = int(next(a for a in args if a.startswith("--maxzoom=")).split("=")[1])
    size = 1000 * (zoom + 1)
    if os.environ.get("FAKE_PMTILES_FAIL"):
        print("boom", file=sys.stderr)
        sys.exit(3)
    if "--dry-run" in args:
        print(f"2026/10/24 19:14:26 extract.go:612: Extract transferred 1 kB "
              f"(overfetch 0.05) for an archive size of {size / 1000:g} kB", file=sys.stderr)
        sys.exit(0)
    with open(out, "wb") as f:
        f.write(b"P" * size)
elif cmd == "verify":
    sys.exit(0 if os.path.getsize(args[1]) else 1)
else:
    sys.exit(2)
