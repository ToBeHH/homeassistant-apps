import datetime
import hashlib
import os
import tempfile
import unittest

from okdl import fetch

from .server import Server

BODY = os.urandom(3 * 1024 * 1024 + 123)
SHA = hashlib.sha256(BODY).hexdigest()


class WindowTest(unittest.TestCase):
    def at(self, hh, mm):
        return datetime.datetime(2026, 10, 24, hh, mm)

    def test_empty_is_always_open(self):
        self.assertTrue(fetch.Window("").is_open(self.at(12, 0)))

    def test_same_day(self):
        w = fetch.Window("09:00-17:00")
        self.assertTrue(w.is_open(self.at(9, 0)))
        self.assertFalse(w.is_open(self.at(17, 0)))
        self.assertEqual(w.seconds_until_open(self.at(8, 0)), 3600)

    def test_across_midnight(self):
        w = fetch.Window("23:00-06:00")
        self.assertTrue(w.is_open(self.at(23, 30)))
        self.assertTrue(w.is_open(self.at(5, 59)))
        self.assertFalse(w.is_open(self.at(12, 0)))
        self.assertEqual(w.seconds_until_open(self.at(22, 0)), 3600)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            fetch.Window("nachts")


class RateLimitTest(unittest.TestCase):
    def test_sleeps_when_ahead(self):
        slept = []
        r = fetch.RateLimit(1, clock=lambda: 0.0, sleep=slept.append)
        r.take(2048)
        self.assertEqual(slept, [2.0])

    def test_unlimited(self):
        slept = []
        fetch.RateLimit(0, clock=lambda: 0.0, sleep=slept.append).take(10**9)
        self.assertEqual(slept, [])


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self.tmp.name, "a_2026-10.zim")

    def tearDown(self):
        self.tmp.cleanup()

    def test_download_and_verify(self):
        with Server() as s:
            s.files["/a"] = BODY
            fetch.download([s.url + "/a"], self.dest, len(BODY), {"sha-256": SHA})
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), BODY)
        self.assertFalse(os.path.exists(self.dest + ".part"))

    def test_resume_with_range(self):
        with open(self.dest + ".part", "wb") as f:
            f.write(BODY[:1000])
        with Server() as s:
            s.files["/a"] = BODY
            fetch.download([s.url + "/a"], self.dest, len(BODY), {"sha-256": SHA})
            self.assertEqual(s.requests, [("/a", "bytes=1000-")])
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), BODY)

    def test_complete_part_is_only_verified(self):
        with open(self.dest + ".part", "wb") as f:
            f.write(BODY)
        with Server() as s:
            fetch.download([s.url + "/a"], self.dest, len(BODY), {"sha-256": SHA})
            self.assertEqual(s.requests, [])
        self.assertTrue(os.path.exists(self.dest))

    def test_next_mirror_on_error(self):
        with Server() as s:
            s.files["/b"] = BODY
            s.fail.add("/a")
            fetch.download(
                [s.url + "/a", s.url + "/b"], self.dest, len(BODY), {"sha-256": SHA}
            )
        self.assertTrue(os.path.exists(self.dest))

    def test_cut_connection_resumes_on_next_mirror(self):
        with Server() as s:
            s.files["/a"] = BODY
            s.files["/b"] = BODY
            s.cut_after = 5000
            fetch.download(
                [s.url + "/a", s.url + "/b"], self.dest, len(BODY), {"sha-256": SHA}
            )
            self.assertEqual(s.requests[1], ("/b", "bytes=5000-"))
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), BODY)

    def test_bad_checksum_never_lands(self):
        with Server() as s:
            s.files["/a"] = BODY
            with self.assertRaises(fetch.DownloadError):
                fetch.download([s.url + "/a"], self.dest, len(BODY), {"sha-256": "0" * 64})
        self.assertFalse(os.path.exists(self.dest))
        self.assertFalse(os.path.exists(self.dest + ".part"))

    def test_md5_fallback(self):
        md5 = hashlib.md5(BODY).hexdigest()
        with Server() as s:
            s.files["/a"] = BODY
            fetch.download([s.url + "/a"], self.dest, len(BODY), {"md5": md5})
        self.assertTrue(os.path.exists(self.dest))

    def test_server_ignoring_range_is_an_error(self):
        with open(self.dest + ".part", "wb") as f:
            f.write(BODY[:1000])
        with Server() as s:
            s.files["/a"] = BODY
            s.ignore_range = True
            with self.assertRaises(fetch.DownloadError):
                fetch.download([s.url + "/a"], self.dest, len(BODY), {"sha-256": SHA})
        # The partial file is kept for a mirror that does support ranges.
        self.assertEqual(os.path.getsize(self.dest + ".part"), 1000)

    def test_closed_window_keeps_part(self):
        class Closed(fetch.Window):
            def is_open(self, now=None):
                return False

        with open(self.dest + ".part", "wb") as f:
            f.write(BODY[:1000])
        with Server() as s:
            s.files["/a"] = BODY
            with self.assertRaises(fetch.OutsideWindow):
                fetch.download(
                    [s.url + "/a"], self.dest, len(BODY), {"sha-256": SHA}, window=Closed()
                )
            self.assertEqual(s.requests, [])
        self.assertEqual(os.path.getsize(self.dest + ".part"), 1000)


if __name__ == "__main__":
    unittest.main()
