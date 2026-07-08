# Python Module — Agent Instructions

This file provides agent-level context for the **entire Python module** of the ETU AI Pipelining project. It covers three independent sub-projects sharing a single Conda runtime.

## Module Structure

```
Python/
├── demo/          → Step-motion video demo (Open CASCADE)
├── MVP/           → Theoretical pipeline (6-stage, pip-installable)
├── src/           → Full engine (CLI + 16 libs + ModelEngine)
├── Project-ETU/   → Conda venv — Python 3.14 runtime (NOT source code)
├── pyproject.toml → Build config (pending update)
└── Python.agent.md → This file
```

> See `Python.md` for the full structure reference.

## Which Implementation to Use?

| When you need to... | Work in |
|--------------------|---------|
| Generate step-motion video, quick visual demos | `demo/` |
| Theoretical validation, structured 6-stage pipeline, tests | `MVP/` |
| Full engine, CLI, library modules, ModelEngine | `src/` |

The three implementations are **independent** — do not cross-import between them.

## Coding Guidelines (All Sub-Projects)

1. **Type hints required** — All functions must have type annotations
2. **Docstrings required** — Google-style docstrings for public API
3. **Use dataclasses** — For data containers
4. **NumPy for arrays** — Prefer numpy over Python lists
5. **Lazy imports** — Import heavy deps (torch, trimesh) inside functions
6. **Test coverage** — Add tests for new features
7. **Never modify `Project-ETU/`** — It is the Conda runtime, not source code

## Quick Reference

| Action | Command |
|--------|---------|
| Run demo | `python Python/demo/main.py` |
| Run MVP CLI | `etu-demo input.png -o output.obj` |
| Run engine CLI | `python Python/src/etu.py <function> [args]` |
| Test (MVP) | `pytest Python/MVP/tests/` |
| Lint | `ruff check Python/MVP/etu_demo/` |
| Format | `black Python/MVP/etu_demo/ Python/MVP/tests/` |
| Type check | `mypy Python/MVP/etu_demo/` |

## MVP Pipeline (Reference)

The MVP implements a 6-stage pipeline via the `PipelineStage` enum:
1. `INPUT` — Load and validate input
2. `PREPROCESS` — Normalize, extract features
3. `INFERENCE` — Run AI model
4. `POSTPROCESS` — Generate mesh (marching cubes)
5. `RENDERING` — Compute normals, prepare buffers
6. `OUTPUT` — Final model

Key classes: `PipelineConfig` (GPU, quality, batch size, limits), `Model` (vertices, faces, normals, UVs).

## Dependencies

Core: `numpy`, `torch`, `trimesh`, `pillow`, `tqdm`
Dev: `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`
Viz: `matplotlib`, `open3d`, `pyglet`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ETU_DEVICE` | Force device (cpu/cuda/mps) | auto |
| `ETU_CACHE_DIR` | Cache directory | `../files/cache` |
| `ETU_LOG_LEVEL` | Logging level | `INFO` |

## Common Tasks

### Add new input format (MVP)
1. Add loader in `utils.py` → `load_input()`
2. Register extension in the suffix check
3. Add test case

### Modify pipeline stage (MVP)
1. Edit method in `pipeline.py`
2. Update `_execute_pipeline()` if changing flow
3. Update tests

### Add CLI option (MVP)
1. Add argument in `main.py` → `create_parser()`
2. Pass to `PipelineConfig`
3. Document in `--help`
