"""Metalink 4 (.meta4) files: size, checksums and mirrors of one ZIM file."""

import dataclasses
import urllib.request
import xml.etree.ElementTree as ET

from . import USER_AGENT

_NS = "{urn:ietf:params:xml:ns:metalink}"


@dataclasses.dataclass(frozen=True)
class Metalink:
    filename: str
    size: int
    hashes: dict  # e.g. {"sha-256": "...", "md5": "..."}
    urls: list  # by priority, best first


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    f = root.find(_NS + "file")
    if f is None:
        raise ValueError("metalink has no <file>")
    hashes = {
        h.get("type"): (h.text or "").strip().lower()
        for h in f.findall(_NS + "hash")
        if h.get("type") and h.text
    }
    urls = []
    for i, u in enumerate(f.findall(_NS + "url")):
        if not (u.text or "").strip().startswith("https://"):
            continue
        try:
            prio = int(u.get("priority", "999999"))
        except ValueError:
            prio = 999999
        urls.append((prio, i, u.text.strip()))
    return Metalink(
        filename=f.get("name", ""),
        size=int(f.findtext(_NS + "size") or 0),
        hashes=hashes,
        urls=[u for _, _, u in sorted(urls)],
    )


def load(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse(resp.read())
