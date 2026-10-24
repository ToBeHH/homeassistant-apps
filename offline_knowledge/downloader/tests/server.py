"""Tiny HTTP server with Range support, serving files from a dict."""

import http.server
import threading


class Server:
    def __init__(self):
        self.files = {}  # path -> bytes
        self.requests = []  # (path, range header)
        self.fail = set()  # paths that answer 500
        self.ignore_range = False
        self.cut_after = None  # close the connection after this many bytes
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                rng = self.headers.get("Range")
                outer.requests.append((self.path, rng))
                if self.path in outer.fail or self.path not in outer.files:
                    self.send_error(500 if self.path in outer.fail else 404)
                    return
                body = outer.files[self.path]
                start = 0
                if rng and not outer.ignore_range:
                    start = int(rng.split("=")[1].split("-")[0])
                    self.send_response(206)
                    self.send_header(
                        "Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}"
                    )
                else:
                    self.send_response(200)
                chunk = body[start:]
                self.send_header("Content-Length", str(len(chunk)))
                self.end_headers()
                if outer.cut_after is not None:
                    chunk = chunk[: outer.cut_after]
                    outer.cut_after = None
                self.wfile.write(chunk)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # Clients hang up on purpose in some tests; keep the output clean.
        self.httpd.handle_error = lambda request, address: None
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
