"""Small control API for the start page, on localhost behind nginx (and with
that behind the Home Assistant login). Also the home of the MCP token."""

import http.server
import json
import logging
import os
import secrets
import threading
import time

log = logging.getLogger(__name__)

PORT = 8098
TRIGGER = "update.trigger"
# Browsers can't send this header across sites without asking first.
CSRF_HEADER = "X-Requested-By"


def read_token(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def new_token(path):
    token = secrets.token_hex(32)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token)
    os.replace(tmp, path)
    return token


def request_update(state_dir):
    with open(os.path.join(state_dir, TRIGGER), "w", encoding="utf-8"):
        pass


def wait_for_update(state_dir, seconds, poll=5):
    """Sleep up to seconds; True as soon as an update was requested."""
    path = os.path.join(state_dir, TRIGGER)
    deadline = time.monotonic() + seconds
    while True:
        if os.path.exists(path):
            os.remove(path)
            return True
        left = deadline - time.monotonic()
        if left <= 0:
            return False
        time.sleep(min(poll, left))


def serve(state_dir, token_file, port=PORT):
    """Start the API in the background; returns the server."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def answer(self, status, data):
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/mcp-token":
                self.answer(200, {"token": read_token(token_file)})
            else:
                self.answer(404, {"error": "not found"})

        def do_POST(self):
            if not self.headers.get(CSRF_HEADER):
                self.answer(403, {"error": f"{CSRF_HEADER} header missing"})
            elif self.path == "/mcp-token":
                log.info("New MCP token created on the start page")
                self.answer(200, {"token": new_token(token_file)})
            elif self.path == "/update":
                log.info("Content check requested")
                request_update(state_dir)
                self.answer(202, {"status": "requested"})
            else:
                self.answer(404, {"error": "not found"})

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
