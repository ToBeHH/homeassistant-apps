"""App options -> list of wanted ZIM names (without date)."""

import json
import os
import re

PROFILES_FILE = os.path.join(os.path.dirname(__file__), "profiles.json")
PROFILES = ("slim", "standard", "full", "custom")

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def load_profiles(path=PROFILES_FILE):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def wanted(profile, languages, extra, profiles=None):
    """ZIM names for a profile and languages, plus extra sources.

    With 'custom' only the extra sources count. Order is kept, duplicates go.
    Returns (names, problems) where problems lists rejected input.
    """
    profiles = load_profiles() if profiles is None else profiles
    problems = []
    names = []
    if profile not in profiles:
        problems.append(f"unknown profile '{profile}'")
        profile = "custom"
    table = profiles.get(profile, {})
    for lang in languages:
        templates = table.get(lang, table.get("*", []))
        names.extend(t.replace("{lang}", lang) for t in templates)
    for name in extra:
        name = name.strip()
        if name.endswith(".zim"):
            problems.append(f"'{name}': give the name without date and .zim")
            continue
        if not _NAME.match(name):
            problems.append(f"'{name}' is not a valid ZIM name")
            continue
        names.append(name)
    return list(dict.fromkeys(names)), problems
