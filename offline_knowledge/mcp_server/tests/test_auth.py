import asyncio
import unittest

from okmcp.auth import BearerAuth

TOKEN = "s3cret-token-0123456789"


class BearerAuthTest(unittest.TestCase):
    def call(self, scope):
        reached = []
        sent = []

        async def app(scope, receive, send):
            reached.append(scope["type"])

        async def send(message):
            sent.append(message)

        asyncio.run(BearerAuth(app, TOKEN)(scope, None, send))
        return reached, sent

    def http(self, *headers):
        return {"type": "http", "headers": list(headers)}

    def test_right_token_passes(self):
        reached, sent = self.call(
            self.http((b"authorization", f"Bearer {TOKEN}".encode()))
        )
        self.assertEqual(reached, ["http"])
        self.assertEqual(sent, [])

    def test_missing_or_wrong_token_is_rejected(self):
        for scope in (
            self.http(),
            self.http((b"authorization", b"Bearer wrong")),
            self.http((b"authorization", TOKEN.encode())),
            self.http((b"x-other", f"Bearer {TOKEN}".encode())),
        ):
            reached, sent = self.call(scope)
            self.assertEqual(reached, [])
            self.assertEqual(sent[0]["status"], 401)

    def test_lifespan_passes(self):
        reached, _ = self.call({"type": "lifespan"})
        self.assertEqual(reached, ["lifespan"])


if __name__ == "__main__":
    unittest.main()
