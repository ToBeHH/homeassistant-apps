"""python3 -m okmcp – serve Zimi's MCP tools on <port>/mcp."""

import argparse
import json
import logging
import sys

from .auth import MIN_TOKEN_LENGTH, BearerAuth


def main(argv=None):
    ap = argparse.ArgumentParser(prog="okmcp", description=__doc__)
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8900)
    args = ap.parse_args(argv)

    with open(args.options, encoding="utf-8") as f:
        options = json.load(f)
    token = options.get("mcp_token") or ""
    if len(token) < MIN_TOKEN_LENGTH:
        sys.exit(f"mcp_token must have at least {MIN_TOKEN_LENGTH} characters")

    # Imported late: these read their paths from the environment on import.
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings
    from zimi import libfolders, mcp_server, server

    # Two log lines per request otherwise.
    logging.getLogger("mcp").setLevel(logging.WARNING)

    server.load_cache()
    # Indexes are built by the library server; this process only reads them.
    # The watcher keeps it in step when the downloader adds or replaces files.
    libfolders.ensure_watch()

    mcp = mcp_server.build(options.get("mcp_tools") or "full")
    mcp.settings.stateless_http = True
    # FastMCP only accepts localhost as Host by default. The token already
    # stops what this protects against: a browser page can't supply it.
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    app = BearerAuth(mcp.streamable_http_app(), token)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
