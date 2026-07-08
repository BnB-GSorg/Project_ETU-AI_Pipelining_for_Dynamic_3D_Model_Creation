# Demo Module - Agent Instructions

This directory contains the **Python demo implementation** of the ETU AI pipeline. Use this for rapid prototyping, research experiments, and as a reference implementation.

## Quick Reference

| Action | Command |
|--------|---------|
| Install | `pip install -e .` |
| Install (dev) | `pip install -e ".[dev]"` |
| Run | `etu-demo input.png -o output.obj` |
| Test | `pytest` |
| Lint | `ruff check src/` |
| Format | `black src/ tests/` |
| Type check | `mypy src/` |

## Directory Structure

```
demo/
├── pyproject.toml          # Project config (dependencies, tools)
├── requirements.txt        # Pip fallback
├── src/etu_demo/           # Main package
│   ├── __init__.py         # Package exports
│   ├── main.py             # CLI entry point
│   ├── pipeline.py         # Core pipeline logic
│   └── utils.py            # I/O and helpers
└── tests/
    └── test_pipeline.py    # Unit tests
```

## Key Classes

### `Pipeline`
Main processing pipeline. Stages:
1. `INPUT` - Load and validate input
2. `PREPROCESS` - Normalize, extract features
3. `INFERENCE` - Run AI model
4. `POSTPROCESS` - Generate mesh (marching cubes)
5. `RENDERING` - Compute normals, prepare buffers
6. `OUTPUT` - Final model

### `PipelineConfig`
Configuration dataclass:
- `use_gpu: bool` - Enable GPU acceleration
- `quality: float` - Quality level (0.0-1.0)
- `batch_size: int` - Batch processing size
- `max_vertices: int` - Vertex limit
- `max_triangles: int` - Triangle limit

### `Model`
Output model dataclass:
- `vertices: np.ndarray` - (N, 3) positions
- `faces: np.ndarray` - (M, 3) triangle indices
- `normals: np.ndarray` - (N, 3) vertex normals
- `uvs: np.ndarray` - (N, 2) texture coordinates

## Coding Guidelines

1. **Type hints required** - All functions must have type annotations
2. **Docstrings required** - Google-style docstrings for public API
3. **Use dataclasses** - For data containers
4. **NumPy for arrays** - Prefer numpy over Python lists
5. **Lazy imports** - Import heavy deps (torch, trimesh) inside functions
6. **Test coverage** - Add tests for new features

## Adding New Features

1. Create feature branch
2. Implement in appropriate module
3. Add type hints and docstrings
4. Add unit tests in `tests/`
5. Run `pytest`, `ruff`, `mypy`
6. Update README if needed

## Dependencies

Core:
- `numpy` - Array operations
- `torch` - AI inference (optional but recommended)
- `trimesh` - Mesh I/O
- `pillow` - Image loading

Optional:
- `open3d` - Point cloud processing
- `scikit-image` - Marching cubes
- `matplotlib` - Visualization

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ETU_DEVICE` | Force device (cpu/cuda/mps) | auto |
| `ETU_CACHE_DIR` | Cache directory | `../files/cache` |
| `ETU_LOG_LEVEL` | Logging level | `INFO` |

## Common Tasks

### Add new input format
1. Add loader in `utils.py` → `load_input()`
2. Register extension in the suffix check
3. Add test case

### Modify pipeline stage
1. Edit method in `pipeline.py`
2. Update `_execute_pipeline()` if changing flow
3. Update tests

### Add CLI option
1. Add argument in `main.py` → `create_parser()`
2. Pass to `PipelineConfig`
3. Document in `--help`
