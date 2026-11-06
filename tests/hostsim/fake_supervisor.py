#!/usr/bin/env python3
"""Answers what bashio asks the Home Assistant Supervisor."""

import http.server
import json


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/services/"):
            self.send_error(400)  # no such service, e.g. no MQTT broker
            return
        if "info" in self.path:
            with open("/sim/info.json", encoding="utf-8") as f:
                data = json.load(f)
        elif "options" in self.path:
            with open("/sim/options.json", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"timezone": "Europe/Berlin", "logging": "info"}
        body = json.dumps({"result": "ok", "data": data}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


http.server.ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
