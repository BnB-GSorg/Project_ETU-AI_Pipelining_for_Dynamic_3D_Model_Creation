# Project ETU — Agent Instructions

Project ETU converts 2D process videos (maths explainers, mechanical
animations, medical visualisations) into interactive 4D scenes — 3D geometry
plus time — that can be orbited, scrubbed and sliced. `WIKI.md` is the deep
technical reference for the format and prior architecture.

The engine is being **rewritten from scratch** in `src/`. The earlier
implementation lives in `ARCHIVED/` as reference only.

## Layout

```
Project-ETU/
├── src/                 # The new engine — all development happens here
│   ├── main.py          #   the command hub (demo, compile, serve, ...)
│   ├── lib.py           #   shared paths, file registry, terminal I/O
│   ├── assets/
│   │   ├── lib/etu/     #   the engine library (formats, kb, ops, brain, vision)
│   │   ├── test/        #   pytest suite + pytest.ini
│   │   └── demo/        #   viewer/, pipeline diagrams, generated demo outputs (out/)
│   │   └── bin/         #   README badge images
│   ├── .env/            #   Local toolchain (never committed)
│   │   ├── Python/etu/  #     the built mamba environment
│   │   └── Zed/         #     editor settings, surfaced via a .zed symlink
│   └── .agents/         #   Local agent infrastructure (never committed)
│       ├── skills/      #     project agent skills
│       └── dev/         #     PLAN.md, PROGRESS.md, agent profiles
├── environment.yml      # Python dependency spec (tracked — single source of truth)
├── ARCHIVED/            # Previous engine — READ ONLY reference
├── AGENTS.md
├── README.md
└── WIKI.md              # Deep technical reference (local only)
```

Only `src/`, `.github/`, `environment.yml`, `AGENTS.md`, `README.md` and
`.gitignore` are tracked. Everything else is intentionally local.

## Toolchain

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12.14 | mamba env at `src/.env/Python/etu` — not a venv |
| ffmpeg | 8.1 | frame extraction for the `watch` command |

## Commands

| Action | Command |
|--------|---------|
| Python | `src/.env/Python/etu/bin/python` |
| Test | `src/.env/Python/etu/bin/pytest src/assets/test` |
| Lint | `src/.env/Python/etu/bin/ruff check src/` |
| Format | `BLACK_CACHE_DIR=/tmp/etu-black src/.env/Python/etu/bin/black src/` |
| Update deps | `mamba env update --prefix src/.env/Python/etu -f environment.yml --prune` |
| Activate | `conda activate ./src/.env/Python/etu` |

Add dependencies by editing `environment.yml` and re-running the update command
— never install ad hoc.

### Two environment quirks, both caused by the long repository path

| Symptom | Fix |
|---------|-----|
| mamba: `Could not find any writable cache directory` | prefix with `CONDA_PKGS_DIRS=src/.env/Python/.pkgs` |
| black: `OSError: AF_UNIX path too long` | prefix with `BLACK_CACHE_DIR=/tmp/etu-black` |

## Skills

Three project skills live in `src/.agents/skills/`:

| Skill | Use it when |
|-------|-------------|
| `etu-dev` | Writing, testing or reviewing code here day to day |
| `etu-bootstrap` | Fresh clone, or the environment is missing/broken |
| `etu-archive-mining` | Reimplementing something the old engine already did |

## Hard rules

1. **Never edit `ARCHIVED/`.** It is frozen reference.
2. **Never copy code out of `ARCHIVED/` into `src/`.** Read it, understand the
   idea, write a simpler version.
3. **Never commit ignored paths.** `src/.env/`, `src/.agents/`,
   `src/assets/demo/out/`, `ARCHIVED/`, `cache/` and `WIKI.md` are local.
   Check `git --no-optional-locks status --short` before every commit, and
   never `git add -f` an ignored path.
4. **Never claim tests or builds pass without running them** and showing output.

## Simplicity is the priority

The previous engine was abandoned for being too complex and hard to read.
Readable beats clever. No speculative abstraction — no plugin systems,
registries or base classes until two real callers exist. Prefer plain data
(dataclasses, dicts) over class hierarchies, small obvious modules over deep
package trees, and the standard library over new dependencies.

If code needs a comment to explain *what* it does, simplify it instead.
Comments explain *why*.

## Maintainer profile

| Preference | Setting |
|------------|---------|
| Maintainer | @dubo651 (BnB-GSorg) |
| Primary language | Python 3.12 (engine + tooling) |
| Coding style | Pragmatic, minimal, readable — simplicity over cleverness |
| Testing | Run before claiming done; pytest |
| Current phase | Ground-up rewrite in `src/`; debugging and rebasing branches |
| Repository | `BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation` |

Ask before installing anything system-wide, before force-adding ignored files,
and before rewriting git history on a shared branch.
