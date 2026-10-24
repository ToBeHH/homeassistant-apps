import hashlib
import json
import os
import tempfile
import unittest

from okdl import sync
from okdl.status import Status

from .server import Server

BODY = b"ZIM" + os.urandom(200_000)

CATALOG = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <name>devdocs_en_bash</name><flavour></flavour>
    <link type="application/x-zim" href="{url}/devdocs_en_bash_2026-10.zim.meta4" length="{size}"/>
  </entry>
</feed>"""

META4 = """<?xml version="1.0" encoding="UTF-8"?>
<metalink xmlns="urn:ietf:params:xml:ns:metalink">
  <file name="devdocs_en_bash_2026-10.zim">
    <size>{size}</size>
    <hash type="sha-256">{sha}</hash>
  </file>
</metalink>"""


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.data = os.path.join(self.root, "share", "ok")
        self.state = os.path.join(self.root, "state")
        os.makedirs(self.state)
        self.status = Status(os.path.join(self.state, "status.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def opts(self, **kw):
        raw = {"data_path": self.data, "profile": "custom", "languages": [],
               "zim_sources": ["devdocs_en_bash"]}
        raw.update(kw)
        return sync.Options(raw)

    def serve(self, s):
        # Served over plain http, so the metalink lists no mirror and the
        # downloader falls back to the URL next to the .meta4.
        s.files["/catalog"] = CATALOG.format(url=s.url, size=len(BODY)).encode()
        s.files["/devdocs_en_bash_2026-10.zim.meta4"] = META4.format(
            size=len(BODY), sha=hashlib.sha256(BODY).hexdigest()
        ).encode()
        s.files["/devdocs_en_bash_2026-10.zim"] = BODY

    def run_sync(self, s, **kw):
        cache = os.path.join(self.state, "catalog.xml")
        return sync.run(self.opts(**kw), self.status, cache, catalog_url=s.url + "/catalog")

    def test_no_storage_no_requests(self):
        for data_path in ("", self.data, "relative/path"):
            with Server() as s:
                self.serve(s)
                self.assertFalse(self.run_sync(s, data_path=data_path))
                self.assertEqual(s.requests, [])
            self.assertEqual(self.status.data["state"], "waiting_for_storage")
        self.assertFalse(os.path.exists(self.data))  # never created by us

    def test_full_run(self):
        os.makedirs(self.data)
        zim_dir = os.path.join(self.data, "zim")
        os.makedirs(zim_dir)
        open(os.path.join(zim_dir, "devdocs_en_bash_2026-08.zim"), "w").close()
        with Server() as s:
            self.serve(s)
            self.assertTrue(self.run_sync(s))
        self.assertEqual(os.listdir(zim_dir), ["devdocs_en_bash_2026-10.zim"])
        with open(os.path.join(self.state, "status.json")) as f:
            st = json.load(f)
        self.assertEqual(st["state"], "idle")
        self.assertEqual(st["items"]["devdocs_en_bash"]["state"], "current")
        self.assertIn("last_success", st)

        # Second run: nothing to do, only the catalog is fetched.
        with Server() as s:
            self.serve(s)
            self.assertTrue(self.run_sync(s))
            self.assertEqual([p for p, _ in s.requests], ["/catalog"])

    def test_unknown_source_does_not_fail(self):
        os.makedirs(self.data)
        with Server() as s:
            self.serve(s)
            self.assertTrue(self.run_sync(s, zim_sources=["devdocs_en_bash", "nope"]))
        self.assertEqual(self.status.data["items"]["nope"]["state"], "unknown")

    def test_no_space(self):
        os.makedirs(self.data)
        old = sync.MIN_RESERVE
        sync.MIN_RESERVE = 10**18
        try:
            with Server() as s:
                self.serve(s)
                self.assertFalse(self.run_sync(s))
        finally:
            sync.MIN_RESERVE = old
        self.assertEqual(self.status.data["items"]["devdocs_en_bash"]["state"], "no_space")
        self.assertEqual(os.listdir(os.path.join(self.data, "zim")), [])


if __name__ == "__main__":
    unittest.main()
