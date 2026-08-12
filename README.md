# Project ETU

Turn a flat 2D process video into an interactive 4D scene — 3D geometry plus
time — that you can orbit, scrub and slice.

## What it does

Most explanatory content is trapped in 2D: a maths animation, a mechanical
walkthrough, a medical process diagram. Humans understand spatial processes
best in 3D. ETU reads a 2D video and re-authors it as a scene you can look at
from any angle, at any point in time.

The output is a single scene file that a viewer can load, play and cut through.

## Status

The engine is being **rewritten from scratch** in `src/`.

The previous implementation is kept in `ARCHIVED/` as reference only. It was
retired for being too complex to read and maintain, so the rewrite prioritises
simplicity: readable beats clever, and no abstraction arrives before a second
caller needs it.

## Layout

```
Project-ETU/
├── src/              # The new engine — all development happens here
├── environment.yml   # Python dependency spec
├── AGENTS.md         # Working agreement, also read by AI coding agents
└── README.md
```

A local `.env/` directory holds the built Python environment and editor
settings, and `ARCHIVED/` holds the previous engine as read-only reference.
Neither is committed — `environment.yml` is all you need to rebuild.

## Prerequisites

| Tool | Version |
|------|---------|
| mamba / conda | 2.6+ / 26+ |
| clang / clang++ | 22+ (C++23) |
| CMake + Ninja | 4.0+ / 1.13+ |
| ffmpeg | 8+ |

## Quick start

Create the local Python environment:

```bash
mamba env create --prefix .env/Python/etu -f environment.yml
```

If mamba complains that it cannot write its package cache, prefix the command
with `CONDA_PKGS_DIRS=.env/Python/.pkgs`.

Then run tools straight from the environment — no activation needed:

```bash
.env/Python/etu/bin/pytest              # test
.env/Python/etu/bin/ruff check src/     # lint
.env/Python/etu/bin/black src/          # format
```

Or activate it if you prefer a shell session:

```bash
conda activate ./.env/Python/etu
```

Once `src/` has a `CMakeLists.txt`, build out of tree:

```bash
cmake -S src -B .env/build -G Ninja
cmake --build .env/build
ctest --test-dir .env/build --output-on-failure
```

## Adding dependencies

Edit `environment.yml`, then apply it:

```bash
mamba env update --prefix .env/Python/etu -f environment.yml --prune
```

`environment.yml` is the single source of truth — never install packages ad hoc.

## Contributing

Development happens in `src/`. `ARCHIVED/` is frozen — read it for ideas, but
never copy from it and never edit it. Keep new code simple and readable; run
the linter and tests before opening a pull request.

See `AGENTS.md` for the full working agreement, including the rules AI agents
follow in this repository.

## License

MIT
