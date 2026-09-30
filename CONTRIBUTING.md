# Contributing

Thanks for helping improve **Wardrive Log Visualizer**. This document is for people developing or packaging the app. End-user download and usage instructions live in [README.md](README.md).

## Repository layout

Keep the **repository root** reserved for project metadata only:

| Path | Purpose |
|------|---------|
| `README.md` | End-user overview |
| `CHANGELOG.md` | Version history — Keep a Changelog + SemVer (**always committed**) |
| `KNOWN_ISSUES.md` | Public acknowledged limitations (**committed**) |
| `LICENSE` | MIT |
| `CONTRIBUTING.md` | This file |
| `.gitignore` | Tells Git which **local** files to skip (must list `LOCAL_NOTES.md`) |
| `docs/images/` | Screenshots and other images for the README |
| `src/` | Application source code |
| `scripts/` | Setup / run / build helpers |
| `requirements/` | Python dependency pins |
| `packaging/` | Installer definitions — when used |

Do **not** add application code, build outputs, or virtualenvs at the root.

**Local only (never commit):** `LOCAL_NOTES.md` (private next-work scratchpad), `settings.xml` (API keys and folder paths), `tests/`, `sample/`, `.venv/`, `build/`, `dist/`, `__pycache__/`, IDE folders, secrets (`.env`), real wardrive `.csv` / `.log` captures.

## Version number (single source of truth)

The app version lives in **one place only**:

```text
src/__init__.py  →  __version__ = "x.y.z"
```

Everything else reads from that value:

- Window title and About dialog
- `python scripts/read_version.py` (used by CI when present)
- GitHub Release tags / asset names (`vX.Y.Z`, `WardriveLogVisualizer-X.Y.Z-…`)

### Stage mapping (Locked)

| Version shape | Stage |
|---------------|--------|
| `0.0.x` | **Alpha** |
| `0.x.x` where minor ≥ 1 (e.g. `0.1.0`) | **Beta** |
| major ≥ 1 (e.g. `1.0.0`) | **Release** |

Status badges in the README should match the stage of `__version__`.

**When shipping a new release:**

1. Bump `__version__` in `src/__init__.py`
2. Update [CHANGELOG.md](CHANGELOG.md) (move items out of Unreleased)
3. Commit and push
4. Run **Build and Release** (when that workflow exists)

Do not hard-code the version in workflows or scripts.

## About `.gitignore`

**`.gitignore` should be committed to GitHub.** It is a normal tracked file.

What should *not* go to GitHub are the paths listed **inside** `.gitignore`, for example:

- `LOCAL_NOTES.md` (private scratchpad)
- `settings.xml` (API keys and folder paths)
- `tests/` and `sample/` (local only)
- `.venv/` (local virtual environment)
- `build/` and `dist/` (PyInstaller outputs)
- `__pycache__/`, IDE folders, local media / data files, `.env`, real capture CSVs

Those stay on your machine (or in CI artifacts).

## Development setup

Requires **Python 3.10+** (development targets **3.14**).

**Windows:**

```bat
scripts\setup_env.bat
```

**Linux / macOS:**

```bash
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
```

This creates `.venv`, upgrades `pip`, and installs packages from `requirements/requirements.txt`.

## Run from source

Building from source is always free and full-featured (same app as packaged builds, once packaging exists).

**Windows:**

```bat
scripts\run_app.bat
```

**Any platform (from the repository root):**

```bash
python -m src
```

## Build locally

Packaging scripts and GitHub Actions workflows will be added when the first portable build lands. Until then, run from source.

## Screenshots

Put PNG/WebP screenshots in [`docs/images/`](docs/images/).

## Code organization

- UI: `src/ui/` (CustomTkinter / dark mode first)
- Core logic: `src/core/` (parsers, merge, map data)
- Prefer small, focused pull requests
- Match existing naming and structure; leave room to expand

## Known issues and local notes

- Public limitations users should know: [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- Maintainer private queue: `LOCAL_NOTES.md` (gitignored — not in the repo clone from GitHub)

## Pull requests

- Keep PRs small and focused
- Don't ship damaging known issues quietly — delay, or disclose loudly
- Update `CHANGELOG.md` under **Unreleased** when your change is user-visible
