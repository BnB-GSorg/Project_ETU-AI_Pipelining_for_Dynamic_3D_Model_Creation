---
description: "Guidelines for Python/MVP/ — structured 6-stage pipeline with type hints, tests, and formatting. Use when editing pipeline.py, utils.py, or tests."
applyTo: "Python/MVP/**"
---

# MVP Module Instructions

## Context
Theoretical-confirmation implementation — structured pip-installable package with a 6-stage AI pipeline: INPUT → PREPROCESS → INFERENCE → POSTPROCESS → RENDERING → OUTPUT.

## Coding Standards
- **Type hints required** on all functions
- **Google-style docstrings** on public API
- **Dataclasses** for data containers (PipelineConfig, Model)
- **NumPy** for arrays — avoid Python lists
- **Lazy imports** for heavy deps (torch, trimesh) — import inside functions

## Key Classes (in `pipeline.py`)
- `PipelineStage` enum — INPUT, PREPROCESS, INFERENCE, POSTPROCESS, RENDERING, OUTPUT
- `PipelineConfig` — use_gpu, quality, batch_size, max_vertices, max_triangles
- `Model` — vertices (N,3), faces (M,3), normals (N,3), uvs (N,2)

## Commands
| Action | Command |
|--------|---------|
| Install | `pip install -e Python/MVP/` |
| Test | `pytest Python/MVP/tests/` |
| Lint | `ruff check Python/MVP/etu_demo/` |
| Format | `black Python/MVP/etu_demo/ Python/MVP/tests/` |
| Type check | `mypy Python/MVP/etu_demo/` |

## Constraints
- Do not import from `Python/demo/` or `Python/src/` — MVP is independent
- Do not modify `Python/Project-ETU/` — it is the Conda runtime
- Always add tests for new features
