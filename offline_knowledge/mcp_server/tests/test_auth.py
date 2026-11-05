import asyncio
import os
import tempfile
import unittest

from okmcp.auth import BearerAuth, TokenFile

TOKEN = "s3cret-token-0123456789"


class BearerAuthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mcp_token")
        self.write(TOKEN + "\n")
        self.tokens = TokenFile(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, self.path)

    def call(self, scope):
        reached = []
        sent = []

        async def app(scope, receive, send):
            reached.append(scope["type"])

        async def send(message):
            sent.append(message)

        asyncio.run(BearerAuth(app, self.tokens)(scope, None, send))
        return reached, sent

    def http(self, token):
        return {"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]}

    def test_right_token_passes(self):
        reached, sent = self.call(self.http(TOKEN))
        self.assertEqual(reached, ["http"])
        self.assertEqual(sent, [])

    def test_missing_or_wrong_token_is_rejected(self):
        for scope in (
            {"type": "http", "headers": []},
            self.http("wrong"),
            {"type": "http", "headers": [(b"authorization", TOKEN.encode())]},
            {"type": "http", "headers": [(b"x-other", f"Bearer {TOKEN}".encode())]},
        ):
            reached, sent = self.call(scope)
            self.assertEqual(reached, [])
            self.assertEqual(sent[0]["status"], 401)

    def test_lifespan_passes(self):
        reached, _ = self.call({"type": "lifespan"})
        self.assertEqual(reached, ["lifespan"])

    def test_new_token_applies_at_once(self):
        self.assertEqual(self.call(self.http(TOKEN))[0], ["http"])
        self.write("new-token-0123456789abc")
        self.assertEqual(self.call(self.http(TOKEN))[0], [])
        self.assertEqual(self.call(self.http("new-token-0123456789abc"))[0], ["http"])

    def test_no_token_rejects_everyone(self):
        for broken in ("", None):
            if broken is None:
                os.remove(self.path)
            else:
                self.write(broken)
            self.assertEqual(self.call(self.http(""))[0], [])


if __name__ == "__main__":
    unittest.main()
