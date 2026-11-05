"""Bearer token check as plain ASGI middleware (no dependencies)."""

import hmac
import os


class TokenFile:
    """The token from a file, re-read when the file changes. The start page
    can replace it while the server runs."""

    def __init__(self, path):
        self.path = path
        self.stamp = None
        self.value = b""

    def bearer(self):
        """The expected header value, or None if there is no usable token."""
        try:
            stamp = os.stat(self.path).st_mtime_ns
            if stamp != self.stamp:
                with open(self.path, encoding="utf-8") as f:
                    self.value = f.read().strip().encode()
                self.stamp = stamp
        except OSError:
            return None
        return b"Bearer " + self.value if self.value else None


class BearerAuth:
    """Rejects every HTTP request without the right token."""

    def __init__(self, app, token_file):
        self.app = app
        self.token_file = token_file

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self._authorized(scope):
            await self.app(scope, receive, send)
            return
        body = b'{"error": "unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    def _authorized(self, scope):
        expected = self.token_file.bearer()
        if expected is None:
            return False
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                return hmac.compare_digest(value, expected)
        return False
