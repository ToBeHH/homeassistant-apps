"""Status file for the landing page and for humans: one JSON document."""

import datetime
import json
import os


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Status:
    def __init__(self, path):
        self.path = path
        self.data = {"state": "starting", "updated": now(), "items": {}}
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            for key in ("last_check", "last_success"):
                if key in old:
                    self.data[key] = old[key]
        except (OSError, ValueError):
            pass

    def set(self, **fields):
        self.data.update(fields)
        self.save()

    def item(self, key, **fields):
        self.data["items"].setdefault(key, {}).update(fields)
        self.save()

    def reset_items(self):
        self.data["items"] = {}

    def save(self):
        self.data["updated"] = now()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
