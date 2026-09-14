# homebrew-lceda

```sh
brew tap ziyangyeh/lceda
brew install --cask lceda-pro
```

| | |
|---|---|
| Tap | `ziyangyeh/lceda` (the GitHub repo is `homebrew-lceda`; `brew` drops the prefix) |
| Cask | `lceda-pro` |

An unofficial Homebrew tap for **嘉立创EDA 专业版** (LCEDA Pro / EasyEDA Pro).

**Apple Silicon only** (`depends_on arch: :arm64`). On an Intel Mac, grab the
x64 build from the [official download page](https://lceda.cn/page/download).

The links on that page are behind a login, but the CDN copies at
`https://image.lceda.cn/files/…` are public — that is what this cask fetches,
byte for byte the installer the website hands out.

## Install

Without tapping first:

```sh
brew install --cask ziyangyeh/lceda/lceda-pro
```

Homebrew now asks whether to trust a third-party cask before loading it; press
return to accept. To trust the whole tap up front (or to install
non-interactively from a script or CI):

```sh
brew trust --tap ziyangyeh/lceda
```

The download is about 350 MB and contains a dmg, which the cask unpacks and
mounts on its own before moving `嘉立创EDA(专业版).app` into `/Applications`.

LCEDA Pro is signed with a Developer ID and notarized by Apple (`spctl -a`
reports `Notarized Developer ID`), so `--no-quarantine` is **not** needed — it
opens on a double-click. If you ever do hit "app is damaged and can't be
opened":

```sh
xattr -dr com.apple.quarantine "/Applications/嘉立创EDA(专业版).app"
```

> Homebrew's own `easyeda` cask (the standard edition, 6.5.x) was disabled on
> 2026-09-01 because it fails the Gatekeeper check. The Pro edition does not
> have that problem.

## Upgrade

```sh
brew update && brew upgrade --cask lceda-pro
```

The app's built-in updater only downloads the new installer to
`~/.config/LCEDA-Pro/updater` and reveals it in Finder — you still have to drag
it across by hand — so it is worth turning off in the settings and letting
`brew upgrade` own this.

## Uninstall

```sh
brew uninstall --cask lceda-pro          # just the app
brew uninstall --zap --cask lceda-pro    # plus settings and caches
```

`--zap` clears `~/.config/LCEDA-Pro` and the related files under `~/Library`,
but deliberately **leaves `~/Documents/LCEDA-Pro` alone** — your projects,
libraries and local database live there.

## Automatic updates

| Workflow | Trigger | What it does |
|---|---|---|
| [`update-cask.yml`](.github/workflows/update-cask.yml) | Daily at 02:20 Asia/Shanghai, plus manual | Scrapes the newest arm64 version from the download page, rewrites the cask, and **verifies before publishing** |
| [`ci.yml`](.github/workflows/ci.yml) | push / PR, plus manual | Runs `brew style` and `brew audit` on a macOS runner; a manual run can also install the cask for real |

A tap has no separate "release" step — `brew` reads `Casks/lceda-pro.rb`
straight off `main`, so committing the file *is* publishing it. That makes the
order matter, and `update-cask.yml` runs:

```
scrape version → rewrite version + sha256 → brew style → brew fetch (downloads
the installer and checks it against the new sha256) → brew audit → commit and
push only if all of that passed
```

Any failing step fails the job with `main` untouched, so a broken cask cannot
reach the people installing from it.

Two switches on a manual run:

- **full-download** — hash the installer locally instead of reading
  `x-obs-content-sha256` off the CDN response (the header matches the file's
  real sha256; it has been checked, and `brew fetch` re-verifies against the
  actual bytes either way);
- **force** — rewrite version and sha256 even when nothing changed upstream.

The same script runs locally:

```sh
python3 scripts/update_cask.py --check-only   # report only, never write
python3 scripts/update_cask.py                # update the cask if there is a newer version
python3 scripts/update_cask.py --trust-header # take the sha256 from the CDN header
```

It needs nothing beyond the Python 3 standard library. By default it streams
the installer to compute the sha256 and cross-checks it against the CDN's
`x-obs-content-sha256` header, failing loudly if the two disagree.

## Notes

Not affiliated with JLC or LCEDA in any way — this only wraps a publicly
available installer as a cask. The software itself is governed by the EULA
shipped inside that installer.
