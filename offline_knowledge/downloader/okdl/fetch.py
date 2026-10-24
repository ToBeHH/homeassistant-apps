"""Resumable, verified download of one file."""

import datetime
import hashlib
import http.client
import logging
import os
import time
import urllib.request

from . import USER_AGENT

log = logging.getLogger(__name__)

CHUNK = 1024 * 1024
PROGRESS_EVERY = 64 * CHUNK


class DownloadError(Exception):
    pass


class OutsideWindow(Exception):
    """The download window closed; the .part file is kept for later."""


class Window:
    """Daily time window 'HH:MM-HH:MM' (may cross midnight). Empty = always."""

    def __init__(self, spec=""):
        spec = (spec or "").strip()
        self.spec = spec
        self.start = self.end = None
        if spec:
            try:
                a, b = spec.split("-")
                self.start = self._parse(a)
                self.end = self._parse(b)
            except ValueError:
                raise ValueError(f"invalid download window '{spec}', use HH:MM-HH:MM")

    @staticmethod
    def _parse(text):
        h, m = text.strip().split(":")
        return datetime.time(int(h), int(m))

    def is_open(self, now=None):
        if self.start is None or self.start == self.end:
            return True
        t = (now or datetime.datetime.now()).time()
        if self.start < self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end

    def seconds_until_open(self, now=None):
        now = now or datetime.datetime.now()
        if self.is_open(now):
            return 0
        start = now.replace(
            hour=self.start.hour, minute=self.start.minute, second=0, microsecond=0
        )
        if start <= now:
            start += datetime.timedelta(days=1)
        return (start - now).total_seconds()


class RateLimit:
    """Simple pacing to a byte rate; 0 = unlimited."""

    def __init__(self, kbytes_per_s=0, clock=time.monotonic, sleep=time.sleep):
        self.rate = max(0, int(kbytes_per_s)) * 1024
        self.clock = clock
        self.sleep = sleep
        self.t0 = clock()
        self.sent = 0

    def take(self, n):
        if not self.rate:
            return
        self.sent += n
        ahead = self.sent / self.rate - (self.clock() - self.t0)
        if ahead > 0:
            self.sleep(ahead)


def _hasher(hashes):
    for kind, algo in (("sha-256", "sha256"), ("md5", "md5")):
        if hashes.get(kind):
            return kind, hashlib.new(algo), hashes[kind]
    return None, None, None


def download(
    urls,
    dest,
    size,
    hashes,
    window=None,
    limit_kbps=0,
    progress=None,
    timeout=60,
):
    """Download to dest via dest.part, trying urls in order.

    Resumes an existing .part with an HTTP Range request. The file is renamed
    to dest only after size and checksum match. Raises OutsideWindow when the
    window closes (keeping .part) and DownloadError when all mirrors fail.
    """
    window = window or Window()
    part = dest + ".part"
    kind, digest, expected = _hasher(hashes)
    hashed = 0  # bytes of .part already fed into digest
    errors = []
    limiter = RateLimit(limit_kbps)

    for url in urls:
        try:
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if size and have > size:
                os.remove(part)
                have = 0
            if digest is not None and hashed != have:
                kind, digest, expected = _hasher(hashes)
                hashed = _feed(digest, part, have)
            if have < size or not size:
                hashed = _fetch(
                    url, part, have, size, digest, window, limiter, progress, timeout
                )
            _verify(part, size, kind, digest, expected)
            os.replace(part, dest)
            return
        except OutsideWindow:
            raise
        except _BadChecksum as err:
            # The bytes on disk are wrong; start over on the next mirror.
            os.remove(part)
            hashed = 0
            kind, digest, expected = _hasher(hashes)
            errors.append(f"{url}: {err}")
            log.warning("%s", errors[-1])
        except (OSError, http.client.HTTPException, DownloadError) as err:
            errors.append(f"{url}: {err}")
            log.warning("Mirror failed: %s", errors[-1])
    raise DownloadError("; ".join(errors) or "no mirror available")


class _BadChecksum(DownloadError):
    pass


def _feed(digest, path, length):
    """Hash the first length bytes of path (resume after a restart)."""
    done = 0
    with open(path, "rb") as f:
        while done < length:
            buf = f.read(min(CHUNK, length - done))
            if not buf:
                break
            digest.update(buf)
            done += len(buf)
    return done


def _fetch(url, part, have, size, digest, window, limiter, progress, timeout):
    if not window.is_open():
        raise OutsideWindow()
    headers = {"User-Agent": USER_AGENT}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if have and resp.status != 206:
            raise DownloadError(f"server ignored the range request ({resp.status})")
        mode = "ab" if have else "wb"
        done = have
        last_report = done
        with open(part, mode) as f:
            while True:
                buf = resp.read(CHUNK)
                if not buf:
                    break
                f.write(buf)
                if digest is not None:
                    digest.update(buf)
                done += len(buf)
                limiter.take(len(buf))
                if progress and done - last_report >= PROGRESS_EVERY:
                    progress(done)
                    last_report = done
                if not window.is_open():
                    f.flush()
                    raise OutsideWindow()
    if progress:
        progress(done)
    if size and done < size:
        raise DownloadError(f"connection closed at {done} of {size} bytes")
    return done


def _verify(part, size, kind, digest, expected):
    actual = os.path.getsize(part)
    if size and actual != size:
        raise _BadChecksum(f"size {actual} != {size}")
    if digest is None:
        log.warning("No checksum published for %s, only the size was checked", part)
        return
    if digest.hexdigest() != expected:
        raise _BadChecksum(f"{kind} mismatch")
