#!/usr/bin/env python3
"""Check lceda.cn for a new 嘉立创EDA专业版 (LCEDA Pro) release and update the cask.

The official download page is public (the *download* itself is behind a login,
but the CDN copy on image.lceda.cn is not), so the version can simply be
scraped from the page and the checksum computed from the CDN file.

Only the Apple Silicon build is tracked; the cask is arm64-only.

Usage:
    python3 scripts/update_cask.py                # check + update if newer
    python3 scripts/update_cask.py --check-only   # only report, never write
    python3 scripts/update_cask.py --force        # rewrite even if unchanged
    python3 scripts/update_cask.py --trust-header # take sha256 from CDN headers
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOWNLOAD_PAGE = "https://lceda.cn/page/download"
FILE_URL = "https://image.lceda.cn/files/lceda-pro-mac-arm64-{version}.zip"
CASK = Path(__file__).resolve().parent.parent / "Casks" / "lceda-pro.rb"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"

RE_VERSION = re.compile(r'^  version "([^"]+)"$', re.M)
RE_SHA256 = re.compile(r'^  sha256 "[^"]*"$', re.M)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def get(url: str, *, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def version_key(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def latest_version() -> str:
    """Scrape the download page for the newest Apple Silicon build."""
    with get(DOWNLOAD_PAGE) as resp:
        html = resp.read().decode("utf-8", "replace")

    hits = re.findall(r"lceda-pro-mac-arm64-(\d+(?:\.\d+)+)\.zip", html)
    if not hits:
        raise SystemExit(f"no lceda-pro-mac-arm64 download found on {DOWNLOAD_PAGE}")
    return max(set(hits), key=version_key)


def header_sha256(url: str) -> str | None:
    """Huawei OBS stores the object checksum in x-obs-content-sha256."""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as resp:
        value = resp.headers.get("x-obs-content-sha256")
    return value if value and re.fullmatch(r"[0-9a-f]{64}", value) else None


def download_sha256(url: str) -> tuple[str, int]:
    """Stream the file and hash it without keeping it on disk."""
    digest = hashlib.sha256()
    size = 0
    with get(url, timeout=300) as resp:
        while chunk := resp.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def checksum(url: str, *, trust_header: bool) -> str:
    advertised = header_sha256(url)
    if trust_header:
        if advertised:
            log(f"  {url} -> {advertised} (from CDN header)")
            return advertised
        log(f"  {url}: no x-obs-content-sha256 header, downloading instead")

    actual, size = download_sha256(url)
    if advertised and advertised != actual:
        raise SystemExit(
            f"checksum mismatch for {url}: CDN advertises {advertised}, "
            f"downloaded {size} bytes hashing to {actual}"
        )
    log(f"  {url} -> {actual} ({size} bytes)")
    return actual


def emit_output(**kwargs: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        for key, value in kwargs.items():
            fh.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true",
                        help="report the upstream version without touching the cask")
    parser.add_argument("--force", action="store_true",
                        help="refresh version and checksum even if nothing changed")
    parser.add_argument("--trust-header", action="store_true",
                        help="read sha256 from the CDN response header instead of downloading")
    args = parser.parse_args()

    text = CASK.read_text(encoding="utf-8")
    match = RE_VERSION.search(text)
    if not match:
        raise SystemExit(f"could not find a version stanza in {CASK}")
    current = match.group(1)

    latest = latest_version()
    log(f"cask: {current}    upstream: {latest}")

    if latest == current and not args.force:
        emit_output(updated="false", version=current, old_version=current)
        log("already up to date")
        return 0

    if version_key(latest) < version_key(current) and not args.force:
        emit_output(updated="false", version=current, old_version=current)
        log(f"upstream {latest} is older than the cask - ignoring")
        return 0

    if args.check_only:
        emit_output(updated="false", version=latest, old_version=current)
        log(f"update available: {current} -> {latest}")
        return 0

    log("computing checksum")
    sha = checksum(FILE_URL.format(version=latest), trust_header=args.trust_header)

    updated = RE_VERSION.sub(f'  version "{latest}"', text, count=1)
    updated, n = RE_SHA256.subn(f'  sha256 "{sha}"', updated, count=1)
    if n != 1:
        raise SystemExit(f"could not find the sha256 stanza in {CASK}")

    if updated == text:
        emit_output(updated="false", version=latest, old_version=current)
        log("cask already matches upstream byte for byte")
        return 0

    CASK.write_text(updated, encoding="utf-8")
    emit_output(updated="true", version=latest, old_version=current)
    log(f"updated {CASK.name}: {current} -> {latest}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as err:
        raise SystemExit(f"network error: {err}") from err
