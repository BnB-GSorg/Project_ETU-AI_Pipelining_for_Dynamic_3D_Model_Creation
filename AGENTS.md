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
├── src/              # The new engine — all development happens here
├── environment.yml   # Python dependency spec (tracked — single source of truth)
├── .env/             # Local toolchain (never committed)
│   ├── Python/etu/   #   the built mamba environment
│   └── Zed/          #   editor settings, surfaced via a .zed symlink
├── .agents/skills/   # Project agent skills (local only)
├── ARCHIVED/         # Previous engine — READ ONLY reference
├── AGENTS.md
├── README.md
└── WIKI.md           # Deep technical reference (local only)
```

Only `src/`, `environment.yml`, `AGENTS.md`, `README.md` and `.gitignore` are
tracked. Everything else is intentionally local.

## Toolchain

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12.13 | mamba env at `.env/Python/etu` — not a venv |
| clang / clang++ | 22.1.4 | Homebrew |
| CMake / Ninja | 4.3.4 / 1.13.2 | build into `.env/build`, never `src/build` |
| ffmpeg | 8.1 | frame extraction |

## Commands

| Action | Command |
|--------|---------|
| Python | `.env/Python/etu/bin/python` |
| Test | `.env/Python/etu/bin/pytest` |
| Lint | `.env/Python/etu/bin/ruff check src/` |
| Format | `.env/Python/etu/bin/black src/` |
| Update deps | `mamba env update --prefix .env/Python/etu -f environment.yml --prune` |
| Activate | `conda activate ./.env/Python/etu` |
| Build C++ | `cmake -S src -B .env/build -G Ninja && cmake --build .env/build` |

Add dependencies by editing `environment.yml` and re-running the update command
— never install ad hoc. If mamba cannot write its cache, prefix commands with
`CONDA_PKGS_DIRS=.env/Python/.pkgs`.

## Skills

Three project skills live in `.agents/skills/`:

| Skill | Use it when |
|-------|-------------|
| `etu-dev` | Writing, testing or reviewing code here day to day |
| `etu-bootstrap` | Fresh clone, or the environment is missing/broken |
| `etu-archive-mining` | Reimplementing something the old engine already did |

## Hard rules

1. **Never edit `ARCHIVED/` or `demo/`.** They are frozen reference.
2. **Never copy code out of `ARCHIVED/` into `src/`.** Read it, understand the
   idea, write a simpler version.
3. **Never commit ignored paths.** `.env/`, `ARCHIVED/`, `demo/`, `.agents/`
   and `WIKI.md` are local. Check `git --no-optional-locks status --short`
   before every commit, and never `git add -f` an ignored path.
4. **Never claim tests or builds pass without running them** and showing output.
5. **Build out of tree** — `.env/build`, never inside `src/`.

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
| Primary languages | C++23 (engine), Python 3.12 (tooling) |
| Coding style | Pragmatic, minimal, readable — simplicity over cleverness |
| Testing | Run before claiming done; pytest + ctest |
| Current phase | Ground-up rewrite in `src/`; debugging and rebasing branches |
| Repository | `BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation` |

Ask before installing anything system-wide, before force-adding ignored files,
and before rewriting git history on a shared branch.
