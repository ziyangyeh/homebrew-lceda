#!/usr/bin/env python3
"""Check lceda.cn for a new 嘉立创EDA专业版 (LCEDA Pro) release and update the tap.

The official download page is public (the *download* itself is behind a login,
but the CDN copy on image.lceda.cn is not), so the version can simply be
scraped from the page and the checksum computed from the CDN file.

Two builds are tracked, because Homebrew has no cask support on Linux:

    Casks/lceda-pro.rb    macOS, Apple Silicon   lceda-pro-mac-arm64-*.zip
    Formula/lceda-pro.rb  Linux, x86_64          lceda-pro-linux-x64-*.zip

Each is versioned on its own. Upstream ships them together today, but a build
that lags behind should not hold the other one back.

Usage:
    python3 scripts/update.py                  # check + update whatever is stale
    python3 scripts/update.py --check-only     # only report, never write
    python3 scripts/update.py --force          # rewrite even if unchanged
    python3 scripts/update.py --trust-header   # take sha256 from CDN headers
    python3 scripts/update.py --only formula   # limit to one target
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DOWNLOAD_PAGE = "https://lceda.cn/page/download"
FILE_URL = "https://image.lceda.cn/files/lceda-pro-{slug}-{version}.zip"
ROOT = Path(__file__).resolve().parent.parent

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"

RE_SHA256 = re.compile(r'^  sha256 "[^"]*"$', re.M)
# The cask declares the version and interpolates it into its url. The formula
# cannot: `url` has to come before `version`, and once brew scans the version
# off the filename `brew audit --strict` rejects a second, redundant copy of
# it. So the formula's only version is the one spelled out in its url, and
# whichever of the two a file uses is the one rewritten here.
RE_VERSION = re.compile(r'^  version "(\d+(?:\.\d+)+)"$', re.M)
RE_URL = re.compile(
    r'^(  url "https://image\.lceda\.cn/files/lceda-pro-[a-z0-9-]+-)'
    r'(\d+(?:\.\d+)+)'
    r'(\.zip")$',
    re.M,
)


@dataclass(frozen=True)
class Target:
    key: str
    path: Path
    slug: str


TARGETS = (
    Target("cask", ROOT / "Casks" / "lceda-pro.rb", "mac-arm64"),
    Target("formula", ROOT / "Formula" / "lceda-pro.rb", "linux-x64"),
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def get(url: str, *, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def version_key(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def latest_versions(slugs: list[str]) -> dict[str, str]:
    """Scrape the download page for the newest build of each slug."""
    with get(DOWNLOAD_PAGE) as resp:
        html = resp.read().decode("utf-8", "replace")

    latest = {}
    for slug in slugs:
        hits = re.findall(rf"lceda-pro-{re.escape(slug)}-(\d+(?:\.\d+)+)\.zip", html)
        if not hits:
            raise SystemExit(f"no lceda-pro-{slug} download found on {DOWNLOAD_PAGE}")
        latest[slug] = max(set(hits), key=version_key)
    return latest


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


def current_version(target: Target, text: str) -> str:
    for pattern, group in ((RE_VERSION, 1), (RE_URL, 2)):
        match = pattern.search(text)
        if match:
            return match.group(group)
    raise SystemExit(f"could not find a version in {target.path}")


def rewrite(target: Target, version: str, sha: str) -> bool:
    """Point the file at `version`/`sha`; return whether anything changed."""
    text = target.path.read_text(encoding="utf-8")

    updated, versions = RE_VERSION.subn(f'  version "{version}"', text, count=1)
    updated, urls = RE_URL.subn(rf"\g<1>{version}\g<3>", updated, count=1)
    if not versions and not urls:
        raise SystemExit(f"could not find a version to rewrite in {target.path}")

    updated, shas = RE_SHA256.subn(f'  sha256 "{sha}"', updated, count=1)
    if shas != 1:
        raise SystemExit(f"could not find the sha256 stanza in {target.path}")

    if updated == text:
        return False
    target.path.write_text(updated, encoding="utf-8")
    return True


def refresh(target: Target, latest: str, args: argparse.Namespace) -> dict[str, str]:
    """Bring one file up to `latest`, unless it is already there."""
    current = current_version(target, target.path.read_text(encoding="utf-8"))

    log(f"{target.key}: {current}    upstream ({target.slug}): {latest}")
    result = {"updated": "false", "version": current, "old_version": current}

    if latest == current and not args.force:
        log(f"  {target.key} is up to date")
        return result

    if version_key(latest) < version_key(current) and not args.force:
        log(f"  upstream {latest} is older than the {target.key} - ignoring")
        return result

    if args.check_only:
        log(f"  update available: {current} -> {latest}")
        return result | {"version": latest}

    log(f"  computing checksum for {target.slug} {latest}")
    sha = checksum(
        FILE_URL.format(slug=target.slug, version=latest),
        trust_header=args.trust_header,
    )

    if not rewrite(target, latest, sha):
        log(f"  {target.path.name} already matches upstream byte for byte")
        return result

    log(f"  updated {target.path.name}: {current} -> {latest}")
    return {"updated": "true", "version": latest, "old_version": current}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true",
                        help="report the upstream version without touching anything")
    parser.add_argument("--force", action="store_true",
                        help="refresh version and checksum even if nothing changed")
    parser.add_argument("--trust-header", action="store_true",
                        help="read sha256 from the CDN response header instead of downloading")
    parser.add_argument("--only", choices=[t.key for t in TARGETS],
                        help="update just one of the two files")
    args = parser.parse_args()

    targets = [t for t in TARGETS if args.only in (None, t.key)]
    latest = latest_versions([t.slug for t in targets])

    results = {t.key: refresh(t, latest[t.slug], args) for t in targets}

    outputs = {"updated": str(any(r["updated"] == "true" for r in results.values())).lower()}
    for key, result in results.items():
        outputs |= {f"{key}_{name}": value for name, value in result.items()}

    summary = "; ".join(
        f"{key} {r['old_version']} -> {r['version']}" if r["updated"] == "true"
        else f"{key} unchanged at {r['version']}"
        for key, r in results.items()
    )
    # Usually one version covers both files; name them all if they diverge.
    landed = sorted({r["version"] for r in results.values() if r["updated"] == "true"})
    outputs["summary"] = summary
    outputs["title"] = f"lceda-pro {' + '.join(landed)}" if landed else "lceda-pro"
    emit_output(**outputs)
    log(summary)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as err:
        raise SystemExit(f"network error: {err}") from err
