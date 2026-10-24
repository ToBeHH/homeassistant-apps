import datetime
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from okdl import maps, sync
from okdl.status import Status

from .server import Server

FAKE = os.path.join(os.path.dirname(__file__), "fake_pmtiles.py")
REGIONS = {
    "world": maps.Region("world", (-180, -85, 180, 85), 6, "World"),
    "germany": maps.Region("germany", (5.8, 47.2, 15.1, 55.1), 15, "Germany"),
}


def fake_extractor():
    return maps.Extractor(command=[sys.executable, FAKE], poll=0.05)


class ParseTest(unittest.TestCase):
    def test_predefined_and_zoom_override(self):
        self.assertEqual(maps.parse("world", REGIONS), REGIONS["world"])
        r = maps.parse("Germany:12", REGIONS)
        self.assertEqual((r.label, r.maxzoom, r.bbox), ("germany", 12, REGIONS["germany"].bbox))

    def test_custom_bbox(self):
        r = maps.parse("home=9.7,53.4,10.3,53.7:15", REGIONS)
        self.assertEqual(r, maps.Region("home", (9.7, 53.4, 10.3, 53.7), 15, "home"))
        self.assertEqual(r.bbox_arg, "9.7,53.4,10.3,53.7")
        self.assertEqual(maps.parse("x=1,2,3,4", REGIONS).maxzoom, maps.CUSTOM_ZOOM)

    def test_invalid(self):
        for spec in ("atlantis", "germany:16", "home=1,2,3", "home=3,2,1,4",
                     "../x=1,2,3,4", "world:x"):
            with self.assertRaises(ValueError, msg=spec):
                maps.parse(spec, REGIONS)

    def test_wanted_reports_problems_and_duplicates(self):
        regions, problems = maps.wanted(["world", "nope", "world:3"], REGIONS)
        self.assertEqual([r.label for r in regions], ["world"])
        self.assertEqual(len(problems), 2)

    def test_shipped_regions_load(self):
        regions = maps.load_regions()
        self.assertIn("world", regions)
        for r in regions.values():
            self.assertEqual(maps.parse(r.label, regions), r)


class BuildsTest(unittest.TestCase):
    def test_latest(self):
        builds = [{"key": "20261023.pmtiles"}, {"key": "20261024.pmtiles"}, {"key": "x.txt"}]
        self.assertEqual(maps.latest_build(builds), "20261024.pmtiles")
        self.assertEqual(maps.build_date("20261024.pmtiles"), datetime.date(2026, 10, 24))
        with self.assertRaises(ValueError):
            maps.latest_build([])

    def test_dry_run_sizes(self):
        line = "extract.go:612: Extract transferred 7.7 GB (overfetch 0.05) for an archive size of 7.4 GB"
        self.assertEqual(maps.parse_dry_run(line), 7_400_000_000)
        self.assertEqual(maps.parse_dry_run("archive size of 45 MB"), 45_000_000)
        self.assertEqual(maps.parse_dry_run("archive size of 860 kB"), 860_000)
        self.assertIsNone(maps.parse_dry_run("nothing here"))


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        open(os.path.join(self.dir, "world.pmtiles"), "w").close()
        self.index = {"regions": {
            "world": maps.index_entry(REGIONS["world"], "20260901.pmtiles", 1),
            "old": {"file": "old.pmtiles", "build": "20260901.pmtiles"},
        }}
        self.today = datetime.date(2026, 10, 24)

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, regions, update_days=30, prune=False):
        return maps.make_plan(regions, self.index, self.dir, "20261024.pmtiles",
                              update_days, prune, today=self.today)

    def test_missing_and_outdated(self):
        p = self.plan([REGIONS["world"], REGIONS["germany"]])
        self.assertEqual([(r.label, why) for r, why in p.extract],
                         [("world", "older than 30 days"), ("germany", "missing")])

    def test_no_updates_with_zero_days(self):
        p = self.plan([REGIONS["world"]], update_days=0)
        self.assertEqual([r.label for r in p.current], ["world"])

    def test_changed_zoom(self):
        p = self.plan([maps.parse("world:5", REGIONS)], update_days=0)
        self.assertEqual(p.extract[0][1], "area or zoom changed")

    def test_prune_and_keep(self):
        self.assertEqual(self.plan([REGIONS["world"]]).keep, ["old"])
        self.assertEqual(self.plan([REGIONS["world"]], prune=True).prune, ["old"])


class ExtractorTest(unittest.TestCase):
    def test_extract_and_dry_run(self):
        ex = fake_extractor()
        r = REGIONS["world"]
        self.assertEqual(ex.dry_run("u", r), 7000)
        with tempfile.TemporaryDirectory() as d:
            part = os.path.join(d, "world.pmtiles.part")
            seen = []
            ex.extract("u", r, part, progress=seen.append)
            self.assertEqual(os.path.getsize(part), 7000)

    def test_failure(self):
        ex = fake_extractor()
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"FAKE_PMTILES_FAIL": "1"}):
            with self.assertRaises(maps.ExtractError):
                ex.extract("u", REGIONS["world"], os.path.join(d, "w.part"))
            self.assertIsNone(ex.dry_run("u", REGIONS["world"]))


class SyncMapsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        os.makedirs(self.data)
        self.status = Status(os.path.join(self.tmp.name, "state", "status.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, s, **kw):
        raw = {"data_path": self.data, "profile": "custom", "languages": [],
               "zim_sources": [], "map_regions": ["world"], "map_update_days": 30}
        raw.update(kw)
        sources = sync.Sources(
            os.path.join(self.tmp.name, "catalog.xml"),
            catalog_url=s.url + "/catalog",
            builds_url=s.url + "/builds.json",
            build_url=s.url + "/{key}",
            extractor=fake_extractor(),
        )
        return sync.run(sync.Options(raw), self.status, sources)

    def serve(self, s, key="20261024.pmtiles"):
        s.files["/builds.json"] = json.dumps([{"key": key}]).encode()

    def test_extract_index_and_rerun(self):
        maps_dir = os.path.join(self.data, "maps")
        with Server() as s:
            self.serve(s)
            self.assertTrue(self.run_sync(s))
            # Without ZIM sources nothing asks the Kiwix catalog.
            self.assertNotIn("/catalog", [p for p, _ in s.requests])
        self.assertEqual(sorted(os.listdir(maps_dir)), ["index.json", "world.pmtiles"])
        with open(os.path.join(maps_dir, "index.json")) as f:
            index = json.load(f)
        self.assertEqual(index["regions"]["world"]["build"], "20261024.pmtiles")
        self.assertEqual(index["regions"]["world"]["size"], 7000)
        self.assertEqual(self.status.data["items"]["map:world"]["state"], "current")

        mtime = os.path.getmtime(os.path.join(maps_dir, "world.pmtiles"))
        with Server() as s:
            self.serve(s, key="20261025.pmtiles")
            self.assertTrue(self.run_sync(s))
        self.assertEqual(os.path.getmtime(os.path.join(maps_dir, "world.pmtiles")), mtime)

    def test_deselected_map_pruned(self):
        with Server() as s:
            self.serve(s)
            self.run_sync(s)
            self.run_sync(s, map_regions=[], prune=True)
        self.assertEqual(os.listdir(os.path.join(self.data, "maps")), ["index.json"])

    def test_failed_extract_leaves_nothing(self):
        with Server() as s, mock.patch.dict(os.environ, {"FAKE_PMTILES_FAIL": "1"}):
            self.serve(s)
            self.assertFalse(self.run_sync(s))
        self.assertEqual(os.listdir(os.path.join(self.data, "maps")), ["index.json"])
        self.assertEqual(self.status.data["items"]["map:world"]["state"], "error")

    def test_build_list_down(self):
        with Server() as s:
            self.assertFalse(self.run_sync(s))


if __name__ == "__main__":
    unittest.main()
