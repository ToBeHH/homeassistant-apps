import json
import os
import stat
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from okdl import control


class ControlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.token_file = os.path.join(self.tmp.name, "mcp_token")
        self.server = control.serve(self.tmp.name, self.token_file, port=0)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def call(self, path, method="GET", headers=None):
        req = urllib.request.Request(self.url + path, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as err:
            with err:
                return err.code, json.load(err)

    def post(self, path):
        return self.call(path, "POST", {control.CSRF_HEADER: "test"})

    def test_token_recreate_replaces_the_old_one(self):
        with open(self.token_file, "w") as f:
            f.write("old\n")
        self.assertEqual(self.call("/mcp-token"), (200, {"token": "old"}))
        status, data = self.post("/mcp-token")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["token"]), 64)
        self.assertEqual(self.call("/mcp-token")[1], data)
        self.assertEqual(stat.S_IMODE(os.stat(self.token_file).st_mode), 0o600)

    def test_post_needs_the_header(self):
        self.assertEqual(self.call("/mcp-token", "POST")[0], 403)
        self.assertEqual(self.call("/update", "POST")[0], 403)
        self.assertFalse(os.path.exists(self.token_file))

    def test_update_wakes_the_waiting_loop_once(self):
        self.assertFalse(control.wait_for_update(self.tmp.name, 0))
        self.assertEqual(self.post("/update")[0], 202)
        start = time.monotonic()
        self.assertTrue(control.wait_for_update(self.tmp.name, 60))
        self.assertLess(time.monotonic() - start, 5)
        self.assertFalse(control.wait_for_update(self.tmp.name, 0))

    def test_unknown_path(self):
        self.assertEqual(self.call("/nope")[0], 404)
        self.assertEqual(self.post("/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
