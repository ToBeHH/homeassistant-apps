"""Compare wanted ZIMs with the catalog and the files on disk."""

import dataclasses
import os
import re

# <name>_<YYYY-MM>[letter].zim, e.g. wiktionary_de_all_nopic_2026-10a.zim
_FILE = re.compile(r"^(?P<key>.+)_(?P<date>\d{4}-\d{2}[a-z]?)\.zim$")
PART = ".part"


def split_filename(filename):
    """'wikipedia_de_all_nopic_2026-10.zim' -> ('wikipedia_de_all_nopic', '2026-10')."""
    m = _FILE.match(filename)
    return (m.group("key"), m.group("date")) if m else (None, None)


def local_files(zim_dir):
    """{key: [filename, ...]} for the ZIM files in zim_dir, oldest first."""
    found = {}
    try:
        names = os.listdir(zim_dir)
    except FileNotFoundError:
        return found
    for name in names:
        key, _ = split_filename(name)
        if key and os.path.isfile(os.path.join(zim_dir, name)):
            found.setdefault(key, []).append(name)
    return {k: sorted(v) for k, v in found.items()}


def part_files(zim_dir):
    try:
        names = os.listdir(zim_dir)
    except FileNotFoundError:
        return []
    return sorted(n for n in names if n.endswith(".zim" + PART))


@dataclasses.dataclass
class Plan:
    current: list = dataclasses.field(default_factory=list)  # [Entry] up to date
    downloads: list = dataclasses.field(default_factory=list)  # [Entry]
    replaces: dict = dataclasses.field(default_factory=dict)  # filename -> [old]
    unknown: list = dataclasses.field(default_factory=list)  # names not in catalog
    obsolete: list = dataclasses.field(default_factory=list)  # old editions
    prune: list = dataclasses.field(default_factory=list)  # deselected, delete
    keep: list = dataclasses.field(default_factory=list)  # deselected, kept
    stale_parts: list = dataclasses.field(default_factory=list)


def make(wanted, catalog, local, parts=(), prune=False):
    """Build the plan.

    wanted: ZIM names; catalog: {key: Entry}; local: {key: [filename]} as from
    local_files(); parts: unfinished '<file>.zim.part' names.
    A key counts as current when its newest catalog file (or a newer one) is
    on disk. Files of
    keys that are no longer wanted are only deleted with prune=True. Older
    editions of a wanted key are deleted after the new one is in place.
    """
    plan = Plan()
    for key in wanted:
        entry = catalog.get(key)
        have = local.get(key, [])
        if entry is None:
            plan.unknown.append(key)
            continue
        # Same key, so the file names differ only in the date and sort by it.
        newest = have[-1] if have else None
        if newest and newest >= entry.filename:
            plan.current.append(entry)
            # Left over when a run stopped between rename and delete.
            plan.obsolete.extend(f for f in have if f != newest)
        else:
            plan.downloads.append(entry)
            plan.replaces[entry.filename] = list(have)
    unwanted = sorted(set(local) - set(wanted))
    for key in unwanted:
        (plan.prune if prune else plan.keep).extend(local[key])
    planned = {e.filename + PART for e in plan.downloads}
    plan.stale_parts = [p for p in parts if p not in planned]
    # Smallest first: something useful arrives early, and a big file that
    # does not fit does not block the rest.
    plan.downloads.sort(key=lambda e: (e.size, e.key))
    return plan
