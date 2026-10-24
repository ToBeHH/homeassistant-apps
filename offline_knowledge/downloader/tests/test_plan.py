import os
import tempfile
import unittest

from okdl import plan, selection
from okdl.catalog import Entry


def entry(key, date, size=100):
    return Entry(key=key, filename=f"{key}_{date}.zim", size=size, meta4_url="u")


PROFILES = {
    "slim": {
        "de": ["wikipedia_de_all_nopic", "wiktionary_de_all_nopic"],
        "*": ["wikipedia_{lang}_all_mini"],
    },
    "custom": {},
}


class SelectionTest(unittest.TestCase):
    def test_language_list_and_template(self):
        names, problems = selection.wanted("slim", ["de", "fr"], [], PROFILES)
        self.assertEqual(
            names,
            ["wikipedia_de_all_nopic", "wiktionary_de_all_nopic", "wikipedia_fr_all_mini"],
        )
        self.assertEqual(problems, [])

    def test_extra_sources_added_once(self):
        names, _ = selection.wanted(
            "slim", ["de"], ["wiktionary_de_all_nopic", "ifixit_de_all"], PROFILES
        )
        self.assertEqual(names[-1], "ifixit_de_all")
        self.assertEqual(names.count("wiktionary_de_all_nopic"), 1)

    def test_custom_is_only_extra(self):
        names, _ = selection.wanted("custom", ["de"], ["devdocs_en_bash"], PROFILES)
        self.assertEqual(names, ["devdocs_en_bash"])

    def test_rejects_filenames_and_paths(self):
        names, problems = selection.wanted(
            "custom", [], ["x_2026-10.zim", "../etc/passwd", " ok_name "], PROFILES
        )
        self.assertEqual(names, ["ok_name"])
        self.assertEqual(len(problems), 2)

    def test_unknown_profile_falls_back_to_custom(self):
        names, problems = selection.wanted("huge", ["de"], [], PROFILES)
        self.assertEqual(names, [])
        self.assertTrue(problems)

    def test_shipped_profiles_load(self):
        profiles = selection.load_profiles()
        self.assertEqual(set(profiles), set(selection.PROFILES))
        for name in ("slim", "standard", "full"):
            self.assertIn("*", profiles[name])


class FilenameTest(unittest.TestCase):
    def test_split(self):
        self.assertEqual(
            plan.split_filename("wiktionary_de_all_nopic_2026-10a.zim"),
            ("wiktionary_de_all_nopic", "2026-10a"),
        )
        self.assertEqual(plan.split_filename("notes.txt"), (None, None))
        self.assertEqual(plan.split_filename("x_2026-10.zim.part"), (None, None))

    def test_local_files(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("a_2026-09.zim", "a_2026-10.zim", "b_2026-01.zim.part", "readme"):
                open(os.path.join(d, n), "w").close()
            self.assertEqual(plan.local_files(d), {"a": ["a_2026-09.zim", "a_2026-10.zim"]})
            self.assertEqual(plan.part_files(d), ["b_2026-01.zim.part"])


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "a": entry("a", "2026-10", size=300),
            "b": entry("b", "2026-10a", size=100),
            "c": entry("c", "2026-08", size=200),
        }

    def test_missing_outdated_current(self):
        local = {"a": ["a_2026-10.zim"], "b": ["b_2026-10.zim"]}
        p = plan.make(["a", "b", "c"], self.catalog, local)
        self.assertEqual([e.key for e in p.current], ["a"])
        self.assertEqual([e.key for e in p.downloads], ["b", "c"])  # smallest first
        self.assertEqual(p.replaces["b_2026-10a.zim"], ["b_2026-10.zim"])
        self.assertEqual(p.replaces["c_2026-08.zim"], [])

    def test_unknown_keeps_local_file(self):
        p = plan.make(["zzz"], self.catalog, {"zzz": ["zzz_2025-01.zim"]}, prune=True)
        self.assertEqual(p.unknown, ["zzz"])
        self.assertEqual(p.prune, [])

    def test_deselected_kept_unless_prune(self):
        local = {"a": ["a_2026-10.zim"], "old": ["old_2025-01.zim"]}
        p = plan.make(["a"], self.catalog, local)
        self.assertEqual(p.keep, ["old_2025-01.zim"])
        self.assertEqual(p.prune, [])
        p = plan.make(["a"], self.catalog, local, prune=True)
        self.assertEqual(p.prune, ["old_2025-01.zim"])

    def test_leftover_old_edition_is_obsolete(self):
        local = {"a": ["a_2026-09.zim", "a_2026-10.zim"]}
        p = plan.make(["a"], self.catalog, local)
        self.assertEqual(p.obsolete, ["a_2026-09.zim"])
        self.assertEqual(p.downloads, [])

    def test_newer_local_file_is_not_downgraded(self):
        p = plan.make(["a"], self.catalog, {"a": ["a_2026-11.zim"]})
        self.assertEqual([e.key for e in p.current], ["a"])
        self.assertEqual(p.downloads, [])
        self.assertEqual(p.obsolete, [])

    def test_stale_parts(self):
        parts = ["c_2026-08.zim.part", "c_2026-07.zim.part", "x_2020-01.zim.part"]
        p = plan.make(["c"], self.catalog, {}, parts)
        self.assertEqual(p.stale_parts, ["c_2026-07.zim.part", "x_2020-01.zim.part"])


if __name__ == "__main__":
    unittest.main()
