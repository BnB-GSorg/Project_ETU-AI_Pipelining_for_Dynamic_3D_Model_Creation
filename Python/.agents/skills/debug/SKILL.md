---
name: debug
description: Python debugging toolkit for the ETU demo pipeline. Covers pdb breakpoints, pytest debugging, profiling (cProfile, memory), GPU/torch debugging, logging, and common crash patterns. Use when tests fail, the pipeline hangs, GPU issues arise, or performance is slow.
---

# ETU Demo Debugging Toolkit

Debug and diagnose issues in the Python demo pipeline. Always start with the fastest diagnostic first, then escalate.

---

## Quick Diagnostic Flow

```
Issue reported?
  ├─ Test failure?   → Section 1 (pytest debugging)
  ├─ Crash/exception? → Section 2 (traceback + pdb)
  ├─ Hangs/slow?     → Section 3 (profiling)
  ├─ GPU issues?     → Section 4 (torch/CUDA/MPS)
  ├─ Wrong output?   → Section 5 (data validation)
  └─ Unknown?        → Section 6 (general triage)
```

---

## 1. Pytest Debugging

### Run a Single Failing Test with Full Traceback

```bash
cd demo
source .venv/bin/activate  # or: .venv\Scripts\activate
pytest -v --tb=long -x tests/test_pipeline.py::TestPipeline::test_process_array
```

| Flag | Purpose |
|------|---------|
| `-v` | Verbose test names |
| `--tb=long` | Full traceback (not truncated) |
| `-x` | Stop on first failure |
| `--pdb` | Drop into pdb on failure |
| `-s` | Show print() output (don't capture) |
| `--lf` | Run only last-failed tests |
| `--ff` | Run failures first, then rest |

### Drop Into Debugger on Failure

```bash
pytest --pdb -x tests/test_pipeline.py
```

### Debug a Specific Test with Breakpoints

```bash
# Insert breakpoint() in the test or source, then:
pytest -s tests/test_pipeline.py::TestPipeline::test_process_array
```

### Isolate Flaky Tests

```bash
# Run test 10 times to catch flakes
pytest --count=10 tests/test_pipeline.py::TestPipeline::test_process_array
```

---

## 2. Traceback & pdb

### Read the Traceback

Open the failing file and go to the bottom of the traceback first (it's usually the real error). Common patterns:

| Error | Common Cause in ETU Demo |
|-------|--------------------------|
| `FileNotFoundError` | Missing input file path (`../files/assets/...`) |
| `ImportError` | Missing `pip install -e .` or missing optional dep |
| `ValueError` | Bad numpy array shape (expects RGB, got RGBA) |
| `RuntimeError` (torch) | GPU OOM or device mismatch |
| `AttributeError` | Calling method on wrong type (config vs pipeline) |
| `KeyError` in `npz` load | Wrong array name in `.npz` file |

### Add a Debug Breakpoint

In `Python/MVP/etu_demo/pipeline.py` or wherever the crash occurs:

```python
breakpoint()  # Drops into pdb

# Common pdb commands:
# p variable_name    → print value
# pp data.shape      → pretty-print
# l                  → list surrounding code
# n                  → next line
# s                  → step into
# c                  → continue
# w                  → show stack trace
# u / d              → up/down stack frame
```

### Post-Mortem Debugging

```python
# In a script that crashes:
import sys
import pdb

try:
    pipeline.process(input_data)
except Exception:
    pdb.post_mortem(sys.exc_info()[2])
```

### Logging (When pdb Isn't Practical)

Add or check logging in the pipeline:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Then in Pipeline methods:
logger.debug("Stage: %s, progress: %.2f", stage, progress)
logger.info("Processing input: shape=%s, dtype=%s", data.shape, data.dtype)
logger.warning("GPU unavailable, falling back to CPU")
logger.error("Pipeline failed at stage: %s", stage, exc_info=True)
```

Check existing logs at:
```bash
# Set level via env var
ETU_LOG_LEVEL=DEBUG pytest -s tests/
```

---

## 3. Profiling (Performance & Memory)

### CPU Profiling with cProfile

```bash
# Profile the CLI
python -m cProfile -s cumulative -m etu_demo.main dummy_input.png -o /dev/null --no-gpu

# Profile a specific test
python -m cProfile -s tottime -m pytest tests/test_pipeline.py::TestPipeline::test_process_array -s

# Generate a visualization (requires snakeviz)
pip install snakeviz
python -m cProfile -o profile.out -m pytest tests/test_pipeline.py
snakeviz profile.out
```

### What to Look For in Profiles

| Pattern | Likely Issue |
|---------|-------------|
| `marching_cubes` dominates | Too many vertices; reduce quality |
| `np.random` is slow | Seed-heavy code; use single seed |
| Repeated `import` calls | Missing lazy import pattern |
| `trimesh.export` slow | Export format issue; try binary |
| `*math*` functions heavy | Vectorize with numpy, not Python math |

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile line-by-line
python -m memory_profiler -m pytest tests/test_pipeline.py::TestPipeline::test_process_array

# Quick check in code:
import tracemalloc
tracemalloc.start()
# ... code ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
```

### Memory Leak Checklist

1. **Clearing model data**: Ensure `Pipeline._execute_pipeline` releases intermediates
2. **GPU tensors**: Tensors stay on GPU until explicitly moved or deleted
3. **Large arrays**: `processed`, `features` might hold large arrays in scope
4. **Callback closures**: Progress callbacks capturing large objects

---

## 4. GPU / Torch Debugging

### Check Device Availability

```python
import torch
print(f"CUDA: {torch.cuda.is_available()}")
print(f"MPS:  {torch.backends.mps.is_available()}")
print(f"CPU:  True")  # Always available

# Check which device etu_demo selected:
from etu_demo import Pipeline
p = Pipeline()
print(f"Active device: {p.device}")
```

### CUDA Debugging

```bash
# Enable CUDA debug mode
CUDA_LAUNCH_BLOCKING=1 pytest -s tests/

# Check GPU memory
nvidia-smi  # Shows memory, utilization, processes
```

### MPS Debugging (macOS)

```bash
# Enable MPS fallback logging
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 pytest -s tests/

# Check if MPS is the bottleneck
# MPS operations are asynchronous; sync for debugging:
torch.mps.synchronize()
```

### Common GPU Issues

| Error | Solution |
|-------|----------|
| `CUDA out of memory` | Reduce batch_size or quality; run `torch.cuda.empty_cache()` |
| `MPS does not support ...` | Operation not supported on MPS; fall back to CPU for that op |
| `device mismatch` | Ensure all tensors are on same device: `tensor.to(device)` |
| GPU not detected | Check `torch.cuda.is_available()` or MPS availability |

### Force CPU for Debugging

```python
# In code:
config = PipelineConfig(use_gpu=False)  # Forces CPU path

# Or via env:
CUDA_VISIBLE_DEVICES="" pytest tests/
```

---

## 5. Data Validation (Wrong Output)

### Validate Pipeline Input

```python
import numpy as np
from pathlib import Path
from etu_demo.utils import load_input

path = Path("input.png")
assert path.exists(), f"File not found: {path}"

data = load_input(path)
print(f"Shape: {data.shape}, dtype: {data.dtype}")
print(f"Range: [{data.min():.3f}, {data.max():.3f}]")

# RGB images should be (H, W, 3), range [0, 1]
assert data.ndim == 3, f"Expected 3D, got {data.ndim}D"
assert data.shape[-1] == 3, f"Expected 3 channels, got {data.shape[-1]}"
```

### Validate Pipeline Output

```python
model = pipeline.process("input.png")

# Basic checks
assert model is not None, "Model is None"
assert len(model.vertices) > 0, "No vertices generated"
assert len(model.faces) > 0, "No faces generated"

# Shape checks
assert model.vertices.shape[1] == 3, f"Vertices should be (N,3), got {model.vertices.shape}"
assert model.faces.shape[1] == 3, f"Faces should be (M,3), got {model.faces.shape}"

# Range check (normalized vertices should be in [-1, 1])
v_min, v_max = model.vertices.min(), model.vertices.max()
print(f"Vertex range: [{v_min:.3f}, {v_max:.3f}]")
if v_min < -2 or v_max > 2:
    print("WARNING: Vertices outside expected range")

# Face index check
max_index = model.faces.max()
assert max_index < len(model.vertices), f"Face references vertex {max_index} but only {len(model.vertices)} exist"

# Normal check
if model.normals is not None:
    norms = np.linalg.norm(model.normals, axis=1)
    bad = np.abs(norms - 1.0) > 0.1
    if bad.any():
        print(f"WARNING: {bad.sum()} non-unit normals")

# Check for degenerate faces
v0 = model.vertices[model.faces[:, 0]]
v1 = model.vertices[model.faces[:, 1]]
v2 = model.vertices[model.faces[:, 2]]
areas = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) / 2
degenerate = areas < 1e-8
if degenerate.any():
    print(f"WARNING: {degenerate.sum()} degenerate faces (zero area)")
```

### Compare Outputs (Diff Two Runs)

```python
# Save reference output
model_ref = pipeline.process("input.png")
np.savez("ref.npz", vertices=model_ref.vertices, faces=model_ref.faces)

# Compare against new run
ref = np.load("ref.npz")
model_new = pipeline.process("input.png")

# Float comparison (deterministic mode required!)
np.testing.assert_allclose(model_new.vertices, ref["vertices"], rtol=1e-5)
```

---

## 6. General Triage

### "It doesn't work" Checklist

1. **Virtual env active?** `which python` should point to `.venv/bin/python`
2. **Package installed?** `pip list | grep etu-demo`
3. **Dependencies fresh?** `pip install -e .` (reinstall)
4. **Python version?** `python --version` must be ≥ 3.10
5. **File paths correct?** Use `Path(__file__).parent / ".."` for relative paths
6. **GPU drivers?** `nvidia-smi` (CUDA) or system report (MPS)
7. **Disk space?** `df -h .` — marching cubes can use temp space

### Minimal Reproduction Script

Create a minimal script to isolate the issue:

```python
# debug_minimal.py — run with: python debug_minimal.py
import numpy as np
from etu_demo import Pipeline, PipelineConfig

# Minimal config
config = PipelineConfig(use_gpu=False, quality=0.5)
pipeline = Pipeline(config)

# Minimal input
input_data = np.random.rand(32, 32, 3).astype(np.float32)

# Single call
model = pipeline.process_array(input_data)
print(f"Success: {len(model.vertices)} vertices, {len(model.faces)} faces")
```

### Enable Verbose Logging

```bash
# Set log level
ETU_LOG_LEVEL=DEBUG python -m etu_demo.main input.png -v

# Or in code:
import logging
logging.getLogger("etu_demo").setLevel(logging.DEBUG)
```

### Common Fixes

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: etu_demo` | `pip install -e .` from `Python/MVP/` |
| `ImportError: No module named 'torch'` | `pip install torch` or skip GPU tests |
| `ImportError: No module named 'trimesh'` | `pip install trimesh` |
| `ImportError: No module named 'skimage'` | `pip install scikit-image` (optional, used for marching cubes) |
| `PermissionError` on output | Check output directory is writable |
| `OSError: [Errno 24] Too many open files` | `ulimit -n 1024` or close file handles |

### Environment Info Dump

Run this to collect debugging context:

```bash
echo "=== System ===" && uname -a
echo "=== Python ===" && python --version && which python
echo "=== Packages ===" && pip list 2>/dev/null | grep -E "etu|torch|numpy|trimesh|skimage"
echo "=== GPU ===" && python -c "import torch; print('CUDA:', torch.cuda.is_available(), 'MPS:', torch.backends.mps.is_available())"
echo "=== Disk ===" && df -h .
```
