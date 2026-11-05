"""Bearer token check as plain ASGI middleware (no dependencies)."""

import hmac

MIN_TOKEN_LENGTH = 16


class BearerAuth:
    """Rejects every HTTP request without the right token."""

    def __init__(self, app, token):
        self.app = app
        self.expected = f"Bearer {token}".encode()

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
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                return hmac.compare_digest(value, self.expected)
        return False
