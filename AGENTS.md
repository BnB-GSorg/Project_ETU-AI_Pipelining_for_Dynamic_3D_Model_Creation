# ETU — Project-Level Agent Instructions

**ETU (Efficient Topology Unfolding)** — AI Pipelining for Dynamic 3D Model Creation.
Accepted at IEEE IICAIET 2026 / IEEE Xplore, 2026.

## Modules

| Module | Role | AGENTS.md |
|--------|------|-----------|
| `src/` | C++23 production core (GPU-accelerated rendering pipeline) | [`src/AGENTS.md`](src/AGENTS.md) |
| `Python/` | Python demo, experimental scaffolding (WIP) | [`Python/AGENTS.md`](Python/AGENTS.md) |
| `docs/` | Wiki, API reference, research materials | [`docs/AGENTS.md`](docs/AGENTS.md) |
| `files/` | Database-like file organization for assets, cache, exports | [`files/AGENTS.md`](files/AGENTS.md) |

## Quick Reference

| Action | Command |
|--------|---------|
| Build C++ core (macOS/Linux) | `cd src && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build` |
| Build C++ core (Windows) | `cd src && cmake -B build -G "Visual Studio 17 2022" && cmake --build build --config Release` |
| Run C++ | `src/build/etu_app` |
| Run Python demo | `cd Python && pip install -e . && cd MVP && etu-demo input.png -o output.obj` |
| Test Python | `cd Python/MVP && python -m pytest` |
| Lint Python | `cd Python/MVP && ruff check etu_demo/ && black --check etu_demo/ tests/` |
| Type-check Python | `cd Python/MVP && mypy etu_demo/` |

## Architecture Overview

```
Input (image / point cloud)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│ pipeline:  Input → Preprocess → Inference →          │
│            Postprocess → Rendering → Output           │
└─────────────────────────────────────────────────────┘
        │
        ▼
Output (OBJ / PLY / STL / glTF / glB)

files/     ← assets/, cache/, exports/ (indexed via index.json)
```

## Pipeline Stages

1. **Input** — Load and validate input (image, point cloud, or native format)
2. **Preprocess** — Normalize, extract features, prepare for inference
3. **Inference** — Run AI model (PyTorch / ONNX in Python; CUDA / MPS in C++)
4. **Postprocess** — Generate mesh via marching cubes or similar
5. **Rendering** — Compute normals, prepare GPU buffers
6. **Output** — Export final model

## Agent Skills

| Skill | Module | Purpose |
|-------|--------|---------|
| `debug` | `Python/` | Python debugging: pdb, pytest, profiling, GPU/torch troubleshooting |
| `debug` | `files/` | Files database: index validation, integrity checks, cache cleanup, schema repair |

## Conventions

- **C++23** required — modern features (`std::expected`, `std::span`, concepts, `constexpr`)
- **Python 3.10+** — type hints required, Google-style docstrings, dataclasses for data containers
- **All code** — test before committing; run module-specific tests before pushing
- **Documentation** — keep wiki pages in sync with implementation; link to `AGENTS.md` files for module-specific guidelines
