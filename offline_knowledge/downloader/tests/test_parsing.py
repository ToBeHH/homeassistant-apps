import os
import unittest

from okdl import catalog, metalink

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.entries = catalog.parse(fixture("catalog.xml"))

    def test_key_is_name_plus_flavour(self):
        self.assertIn("wikipedia_de_all_nopic", self.entries)
        self.assertIn("devdocs_en_bash", self.entries)

    def test_entry_fields(self):
        e = self.entries["wiktionary_de_all_nopic"]
        self.assertEqual(e.filename, "wiktionary_de_all_nopic_2026-10a.zim")
        self.assertEqual(e.size, 1600000000)
        self.assertTrue(e.meta4_url.endswith(".zim.meta4"))
        self.assertEqual(e.language, "deu")

    def test_entry_without_file_is_skipped(self):
        self.assertNotIn("broken_entry", self.entries)

    def test_load_falls_back_to_cache(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "catalog.xml")
            with open(cache, "wb") as f:
                f.write(fixture("catalog.xml"))
            entries = catalog.load(cache, url="http://127.0.0.1:9/nothing", timeout=2)
            self.assertIn("devdocs_en_bash", entries)

    def test_load_without_cache_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception):
                catalog.load(os.path.join(d, "x.xml"), url="http://127.0.0.1:9/", timeout=2)


class MetalinkTest(unittest.TestCase):
    def setUp(self):
        self.m = metalink.parse(fixture("file.meta4"))

    def test_fields(self):
        self.assertEqual(self.m.filename, "devdocs_en_bash_2026-10.zim")
        self.assertEqual(self.m.size, 572117)

    def test_hashes_lowercase(self):
        self.assertEqual(
            self.m.hashes["sha-256"],
            "ea4afb04ddf90f31363829ef9fa2485405dc05bd1fc62b4626245fe70c24735d",
        )
        self.assertEqual(self.m.hashes["md5"], "16955e8143f5972926ac4460f927ba86")

    def test_urls_by_priority_https_only(self):
        self.assertEqual(
            self.m.urls,
            [
                "https://ftp.fau.de/kiwix/zim/devdocs/devdocs_en_bash_2026-10.zim",
                "https://ftp.nluug.nl/pub/kiwix/zim/devdocs/devdocs_en_bash_2026-10.zim",
            ],
        )


if __name__ == "__main__":
    unittest.main()
