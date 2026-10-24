"""Kiwix OPDS catalog: ZIM name without date -> newest published file."""

import dataclasses
import logging
import os
import urllib.request
import xml.etree.ElementTree as ET

from . import USER_AGENT

log = logging.getLogger(__name__)

CATALOG_URL = "https://library.kiwix.org/catalog/v2/entries?count=-1"
ZIM_TYPE = "application/x-zim"
_ATOM = "{http://www.w3.org/2005/Atom}"


@dataclasses.dataclass(frozen=True)
class Entry:
    key: str  # e.g. wikipedia_de_all_nopic
    filename: str  # e.g. wikipedia_de_all_nopic_2026-10.zim
    size: int  # bytes, as announced by the catalog
    meta4_url: str
    title: str = ""
    language: str = ""


def _key(name, flavour):
    return f"{name}_{flavour}" if flavour else name


def parse(xml_bytes):
    """Parse an OPDS acquisition feed into {key: Entry}.

    The catalog lists one entry per name and flavour, always the newest file.
    Should a key appear twice anyway, the later file name wins.
    """
    root = ET.fromstring(xml_bytes)
    entries = {}
    for e in root.iter(_ATOM + "entry"):
        name = (e.findtext(_ATOM + "name") or "").strip()
        if not name:
            continue
        link = next(
            (l for l in e.iter(_ATOM + "link") if l.get("type") == ZIM_TYPE), None
        )
        if link is None or not link.get("href"):
            continue
        href = link.get("href")
        filename = href.rsplit("/", 1)[-1]
        if filename.endswith(".meta4"):
            filename = filename[: -len(".meta4")]
        entry = Entry(
            key=_key(name, (e.findtext(_ATOM + "flavour") or "").strip()),
            filename=filename,
            size=int(link.get("length") or 0),
            meta4_url=href,
            title=(e.findtext(_ATOM + "title") or "").strip(),
            language=(e.findtext(_ATOM + "language") or "").strip(),
        )
        old = entries.get(entry.key)
        if old is None or entry.filename > old.filename:
            entries[entry.key] = entry
    return entries


def load(cache_path, url=CATALOG_URL, timeout=120):
    """Fetch the catalog, falling back to the last cached copy when offline."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        entries = parse(data)
        if not entries:
            raise ValueError("catalog is empty")
    except Exception as err:  # network, HTTP or XML error
        if not os.path.exists(cache_path):
            raise
        log.warning("Catalog not reachable (%s), using cached copy", err)
        with open(cache_path, "rb") as f:
            return parse(f.read())
    tmp = cache_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, cache_path)
    return entries
