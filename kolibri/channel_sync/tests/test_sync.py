import http.server
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from kbsync import sync
from kbsync.__main__ import wait_for_trigger

CH = "5d53b37cc90e50128a40e293d9fadb27"
META = {"id": CH, "name": "Test", "version": 3, "published_size": 1000}


class Studio:
    """/lookup answers with META for CH, 404 otherwise."""

    def __enter__(self):
        self.requests = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                outer.requests.append(self.path)
                if not self.path.endswith(CH):
                    self.send_error(404)
                    return
                body = json.dumps([META]).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


class TriggerTest(unittest.TestCase):
    def test_trigger_wakes_once(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "trigger")
            self.assertFalse(wait_for_trigger(path, 0))
            open(path, "w").close()
            self.assertTrue(wait_for_trigger(path, 60))
            self.assertFalse(os.path.exists(path))


class RunOnceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "state.json")
        self.calls = []
        self.result = 0

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        self.calls.append(args)
        return self.result

    def sync(self, studio, channels=CH, data_path=None):
        options = {
            "data_path": self.tmp.name if data_path is None else data_path,
            "channels": [channels] if isinstance(channels, str) else list(channels),
        }
        return sync.run_once(options, self.state, studio.url, self.run_cmd)

    def test_import_and_then_up_to_date(self):
        with Studio() as s:
            self.assertTrue(self.sync(s))
            self.assertEqual(
                self.calls,
                [("importchannel", "network", CH), ("importcontent", "network", CH)],
            )
            self.calls.clear()
            self.assertTrue(self.sync(s))
            self.assertEqual(self.calls, [])

    def test_new_version_imports_again(self):
        sync.write_state(self.state, {CH: {"version": 2, "complete": True}})
        with Studio() as s:
            self.assertTrue(self.sync(s))
        self.assertEqual(len(self.calls), 2)

    def test_failure_is_retried(self):
        self.result = 1
        with Studio() as s:
            self.assertFalse(self.sync(s))
            self.assertEqual(len(self.calls), 1)  # content not tried
            self.assertFalse(sync.read_state(self.state)[CH]["complete"])
            self.result = 0
            self.assertTrue(self.sync(s))
        self.assertTrue(sync.read_state(self.state)[CH]["complete"])

    def test_no_storage_no_requests(self):
        for data_path in ("", "/does/not/exist", "relative"):
            with Studio() as s:
                self.assertFalse(self.sync(s, data_path=data_path))
                self.assertEqual(s.requests, [])
        self.assertEqual(self.calls, [])

    def test_no_channels_is_fine_without_storage(self):
        with Studio() as s:
            self.assertTrue(self.sync(s, channels=[], data_path=""))

    def test_unknown_and_invalid_ids_are_skipped(self):
        with Studio() as s:
            self.assertTrue(self.sync(s, channels=["f" * 32, "../etc/passwd"]))
            self.assertEqual(len(s.requests), 1)
        self.assertEqual(self.calls, [])

    def test_no_space_skips_new_channel(self):
        with Studio() as s, mock.patch.object(sync, "MIN_RESERVE", 10**18):
            self.assertFalse(self.sync(s))
        self.assertEqual(self.calls, [])

    def test_started_channel_needs_no_full_size(self):
        self.assertEqual(sync.bytes_needed(META, None), 1000)
        self.assertEqual(sync.bytes_needed(META, {"version": 2}), 0)


if __name__ == "__main__":
    unittest.main()
