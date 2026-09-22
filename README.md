# homebrew-lceda

```sh
brew tap ziyangyeh/lceda

brew install --cask lceda-pro   # macOS, Apple Silicon
brew install lceda-pro          # Linux, x86_64
```

| | |
|---|---|
| Tap | `ziyangyeh/lceda` (the GitHub repo is `homebrew-lceda`; `brew` drops the prefix) |
| Cask | `lceda-pro` — macOS, Apple Silicon |
| Formula | `lceda-pro` — Linux, x86\_64 |

An unofficial Homebrew tap for **嘉立创EDA 专业版** (LCEDA Pro / EasyEDA Pro).

Two files for one app, because **Homebrew has no cask support on Linux**: macOS
gets a cask that drops `嘉立创EDA(专业版).app` into `/Applications`, Linux gets a
formula that unpacks the Electron tree into the Cellar. They share a name and
are versioned independently, so a build that lags upstream never holds the
other one back.

Other builds upstream ships — Intel Mac, Windows, Linux arm64/loong64/sw64 —
are not tracked; grab those from the
[official download page](https://lceda.cn/page/download).

The links on that page are behind a login, but the CDN copies at
`https://image.lceda.cn/files/…` are public — that is what this tap fetches,
byte for byte the installer the website hands out.

## Install

Without tapping first:

```sh
brew install --cask ziyangyeh/lceda/lceda-pro   # macOS
brew install ziyangyeh/lceda/lceda-pro          # Linux
```

Homebrew asks whether to trust a third-party cask or formula before loading it;
press return to accept. To trust the whole tap up front (or to install
non-interactively from a script or CI):

```sh
brew trust --tap ziyangyeh/lceda
```

> **On macOS, `--cask` is not optional.** When a tap holds a formula and a cask
> under the same name, `brew install lceda-pro` resolves to the *formula* and
> stops with `lceda-pro: Linux is required for this software.` Homebrew prints
> the way out right above that error, but it is easier to just write `--cask`.

### macOS

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

### Linux

Needs x86\_64 and a GTK 3 desktop session. The download is about 346 MB and
unpacks to roughly 1.1 GB in the Cellar.

`brew install lceda-pro` prints `Treating lceda-pro as a formula. For the cask,
use …` before it gets going. Ignore it — that is the same name-sharing notice
macOS gets, and here it is already doing the right thing; there is no cask to
switch to on Linux. `brew install --formula lceda-pro` silences it.

What lands where:

| | |
|---|---|
| `$(brew --prefix)/bin/lceda-pro` | small shell wrapper around the Electron binary |
| `$(brew --prefix)/opt/lceda-pro/libexec/` | the app itself |
| `$(brew --prefix)/share/applications/lceda-pro.desktop` | launcher entry |
| `$(brew --prefix)/share/icons/hicolor/*/apps/lceda-pro.png` | icons, nine sizes |

Desktop environments only read that `share` directory if it is on
`XDG_DATA_DIRS`, and `brew shellenv` does **not** put it there:

```sh
export XDG_DATA_DIRS="$(brew --prefix)/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
```

Log out and back in for 嘉立创EDA(专业版) to appear in the application menu;
`lceda-pro` works from the shell either way.

The wrapper launches with `--no-sandbox --gtk-version=3`, which is exactly what
upstream's own desktop entry does. The bundled `chrome-sandbox` would have to
be setuid root to be usable, and `brew install` does not run as root — upstream
sidesteps the same problem by `chmod -R 777`-ing its tree and passing
`--no-sandbox`.

## Upgrade

```sh
brew update && brew upgrade --cask lceda-pro   # macOS
brew update && brew upgrade lceda-pro          # Linux
```

The app's built-in updater only downloads the new installer to
`~/.config/LCEDA-Pro/updater` and reveals it in the file manager — you still
have to move it across by hand — so it is worth turning off in the settings and
letting `brew upgrade` own this.

## Uninstall

```sh
brew uninstall --cask lceda-pro          # macOS: just the app
brew uninstall --zap --cask lceda-pro    # macOS: plus settings and caches
brew uninstall lceda-pro                 # Linux
```

`--zap` clears `~/.config/LCEDA-Pro` and the related files under `~/Library`.
Formulae have no `zap`, so on Linux remove `~/.config/LCEDA-Pro` by hand if you
want the settings gone.

Neither one touches **`~/Documents/LCEDA-Pro`** — your projects, libraries and
local database live there, and they are deliberately left behind.

## Automatic updates

| Workflow | Trigger | What it does |
|---|---|---|
| [`update.yml`](.github/workflows/update.yml) | Daily at 02:20 Asia/Shanghai, plus manual | Scrapes both builds off the download page, rewrites cask and formula, and **verifies before publishing** |
| [`ci.yml`](.github/workflows/ci.yml) | push / PR, plus manual | `brew style` and `brew audit` for the cask on macOS and the formula on Linux; a manual run can also install for real |

A tap has no separate "release" step — `brew` reads the files straight off
`main`, so committing them *is* publishing. That makes the order matter, and
`update.yml` runs:

```
                  scrape versions → rewrite cask + formula
                                  ↓
                    handed to the verify jobs as an artifact
                        ↙                              ↘
        verify cask (macOS runner)          verify formula (Linux runner)
        style → fetch → audit               style → fetch → audit
                        ↘                              ↙
                  commit and push, only if both passed
```

`brew fetch` downloads the installer and checks it against the sha256 just
written, so nothing reaches `main` on the strength of a scraped header alone.
Any failing step fails the job with `main` untouched, and the next day's run
picks it up again — a flaky `--online` audit costs a day, not a broken tap.

Two switches on a manual run:

- **full-download** — hash the installers locally instead of reading
  `x-obs-content-sha256` off the CDN response (the header matches the file's
  real sha256; it has been checked, and `brew fetch` re-verifies against the
  actual bytes either way);
- **force** — rewrite version and sha256 even when nothing changed upstream.

The same script runs locally:

```sh
python3 scripts/update.py --check-only     # report only, never write
python3 scripts/update.py                  # update whichever file is stale
python3 scripts/update.py --trust-header   # take the sha256 from the CDN header
python3 scripts/update.py --only formula   # limit it to one of the two
```

It needs nothing beyond the Python 3 standard library. By default it streams
each installer to compute the sha256 and cross-checks it against the CDN's
`x-obs-content-sha256` header, failing loudly if the two disagree.

One asymmetry worth knowing if you edit the files by hand: the cask declares
`version` and interpolates it into its `url`, while the formula cannot — `url`
has to come before `version`, and once `brew` scans the version off the
filename, `brew audit --strict` rejects a second copy of it. So the formula's
only version number is the one inside its URL, and the script rewrites
whichever form a file uses.

## Notes

Not affiliated with JLC or LCEDA in any way — this only wraps a publicly
available installer. The software itself is governed by the EULA shipped inside
that installer.
