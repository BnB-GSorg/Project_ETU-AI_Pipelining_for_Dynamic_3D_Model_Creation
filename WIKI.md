# Project ETU — Technical Wiki

> *"How to create a tool to better understand anything?"*
>
> Conceived June 17, 2026 in England. Built across June–July 2026.

---

## 1. Overview

Project ETU (Enhanced Temporal Understanding) converts 2D process videos — math explainers, chemical reactions, mechanical animations, medical visualizations — into interactive 4D (3D + time) representations. The output is a single `.mmi` file that can be orbited, scrubbed, sliced, and inspected from any angle at any timepoint.

The core insight: humans comprehend spatial processes best in 3D, but most educational content is trapped in 2D. ETU bridges that gap.

---

## 2. Architecture — Two Pipelines

ETU has two independent pipelines that converge on the same output format:

### 2.1 Dimensional Lifting Pipeline (active, single-view)

For **flat 2D animations** (3Blue1Brown-style, cartoon explainers, simulator outputs) where there is no hidden depth to reconstruct. Instead, the system *understands* what the video shows and *re-authors* it as a 3D scene.

```
Video (single-view)
  │
  ├─ [ingest] → dense frame pool (~10 fps, up to 240 frames)
  │
  ├─ [change-driven sampling] → ~8–12 frames weighted toward visual change
  │     Algorithm: cheap grayscale pixel diffs → pick equal-change samples
  │
  ├─ [vision "eye"] → Gemini 2.5 Flash describes frames → FeatureGraph
  │     Output: domain-agnostic JSON of objects, positions, colors, shapes, motion
  │
  ├─ [identity reconciliation] → union-find merge of split/duplicate IDs
  │     Vision models often label the same object "b1" then "b2" across frames
  │
  ├─ [router] → two paths:
  │   ├─ Template upgrade: DeepSeek classifies → known math template → correct 3D
  │   │     (fourier_stack, complex_surface, graph_surface, taylor_series,
  │   │      vector_field, linear_transform, parametric_surface)
  │   └─ General lift: FeatureGraph → 3D primitives → scene (works on ANYTHING)
  │         Depth on Z-axis is an honest approximation from the vision model's guess
  │
  └─ [output] → mmi-lite JSON → Three.js viewer
```

### 2.2 Reconstruction Pipeline (multi-view, GPU — new)

For **multi-view video** where multiple synchronized cameras film the same process from different angles. True 3D depth is recovered via photogrammetry and neural rendering.

```
Multi-view video [cam0, cam1, cam2, ...].mp4
  │
  ├─ [ingest] → per-view frame pools, sync-verified
  │
  ├─ [keyframes] → content-based frame selection on reference view (view 0)
  │
  ├─ [reconstruct] → one of three backends:
  │   ├─ colmap:   classic SfM+MVS, CPU-feasible, per time-window
  │   ├─ 3dgs:     3D Gaussian Splatting, GPU, high quality, per window
  │   └─ dyn-nerf: 4D Gaussian Splatting / Dynamic NeRF, GPU, single model
  │     Output: per-frame TimeSlices — world-space point clouds (N,3) + colors
  │
  ├─ [segment] → k-means color clustering → per-point part labels
  │
  ├─ [track] → Kabsch rigid alignment between consecutive frames per part
  │     Output: per-part keyframes {t, position, quaternion}
  │
  ├─ [encode_git] → transform keyframes into matrix-chain commits → mmi-git
  │
  └─ [output] → mmi-git file → Three.js viewer
```

### 2.3 Which pipeline to use

| Situation | Pipeline | Backend |
|-----------|----------|---------|
| Single flat animation (math, diagrams) | Dimensional lifting | Auto (Gemini + DeepSeek) |
| 2+ synced cameras, static-ish process | Reconstruction | `colmap` |
| 2+ synced cameras, want high quality | Reconstruction | `3dgs` |
| 2+ synced cameras, highly dynamic | Reconstruction | `dyn-nerf` |
| No GPU, just testing pipeline flow | Reconstruction | `synthetic` |

---

## 3. The mmi-git Format

### 3.1 Design Philosophy

Inspired by git's model of version control: instead of storing a full snapshot of every frame (wasteful — most frames are nearly identical), store a **base point cloud** at frame 0 plus a **chain of transformation matrices** (one per frame, one per part). Each commit is a 4×4 homogeneous matrix encoding rotation + translation + scale.

This is the "spatial git": git records text changes as line diffs; mmi-git records spatial changes as matrix multiplications.

### 3.2 File Structure

```json
{
  "format": "mmi-git",
  "version": "0.1",
  "meta": {
    "title": "Reconstructed Process",
    "fps": 10,
    "duration_frames": 120,
    "source": "reconstruction:3dgs",
    "coordinate_system": "right-handed-y-up",
    "events": [{"t": 0, "label": "Reaction begins"}]
  },
  "base": {
    "points": [x0,y0,z0, x1,y1,z1, ...],    // flat float array, (N*3) values
    "colors": [r0,g0,b0, r1,g1,b1, ...]       // optional, (N*3) values in 0..1
  },
  "parts": [
    {
      "id": "part_00",
      "label": "Blue reagent",
      "point_indices": [0, 1, 2, ..., 149],   // indices into base.points
      "color": "#3b82f6"
    }
  ],
  "commits": [
    {
      "t": 1,
      "transforms": {
        "part_00": [m00,m01,m02,m03, m10,...,m13, m20,...,m23, m30,...,m33],
        "part_01": [m00,m01,m02,m03, ...]     // 16 floats per part, row-major
      }
    }
  ],
  "keyframes": [
    {
      "t": 30,
      "parts": {
        "part_00": [x0,y0,z0, x1,y1,z1, ...],  // full snapshot at frame 30
        "part_01": [x0,y0,z0, ...]
      }
    }
  ],
  "layers": [{"id": "part_00", "name": "Blue reagent", "color": "#3b82f6"}]
}
```

### 3.3 Commit Semantics

A commit at frame `t` records the **delta** from the previous frame to frame `t`. Commits are whole-scene: all parts have a transform in every commit (identity matrix for parts that didn't change at that frame).

The 4×4 matrix encodes the full rigid+scale transform:

```
M = [R₃ₓ₃  T₃ₓ₁]
    [0₁ₓ₃  1   ]

Where R = rotation matrix, T = translation vector.
```

To render frame N:
1. Find nearest keyframe ≤ N (or base if none)
2. Initialize per-part positions from that keyframe
3. For each commit with t in (keyframe_t, N]:
   - For each part, apply its commit's 4×4 matrix to all its points:
     ```
     P' = M @ [x, y, z, 1]ᵀ  →  take first 3 components
     ```

### 3.4 Keyframes

Periodic full snapshots (every ~30 frames by default) bound random-access cost to O(KEYFRAME_INTERVAL). Without them, seeking to frame 500 would require replaying 499 matrix multiplications. With them, at most 29.

### 3.5 Storage Efficiency

| Approach | 100-frame scene, 5000 points, 3 parts |
|----------|--------------------------------------|
| Full per-frame snapshots | ~100 × 45KB = 4.5 MB |
| mmi-git (base + commits) | 1 × 45KB + 99 × 3×(16×8) bytes ≈ 45KB + 38KB = 83 KB |
| **Compression ratio** | **~54:1** |

The win grows with frame count. For a 1000-frame scene, mmi-git is ~500× smaller.

### 3.6 Format Versioning

| Version | Changes |
|---------|---------|
| 0.1 | Initial: base + commits + keyframes, 4×4 homogeneous matrices |

---

## 4. Coordinate System

- **Right-handed, Y-up**: +X right, +Y up, +Z toward viewer
- **Quaternions**: [x, y, z, w] order (Three.js convention)
- **Matrices**: row-major in JSON, converted to column-major for Three.js

---

## 5. Technical Stack

### 5.1 Core (Python)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frame I/O | OpenCV / ffmpeg | Video ingestion, frame extraction |
| Vision | Gemini 2.5 Flash | Frame description, FeatureGraph extraction |
| Reasoning | DeepSeek (text-only) | Template classification, parameter filling |
| Math | numpy | Point clouds, matrix ops, SVD/Kabsch |
| 3D reconstruction | COLMAP, gsplat | SfM, MVS, Gaussian Splatting |

### 5.2 Viewer (JavaScript)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Renderer | Three.js (ES modules, no build step) | WebGL 3D rendering |
| Controls | OrbitControls | Camera orbit, pan, zoom |
| Format | mmi-lite, mmi-git | Scene description |
| Deployment | Python http.server | Zero-dependency local serving |

### 5.3 Format

| Format | Status | Description |
|--------|--------|-------------|
| mmi-lite | Stable | Per-object keyframe tracks, multiple geometry types |
| mmi-git | New (v0.1) | Base + commit-chain delta storage |

---

## 6. Detailed Usage

### 6.1 Installation

```bash
cd ana_eng_ver2
pip install -r requirements.txt
```

Core dependencies: `numpy`, `opencv-python` (or ffmpeg on PATH).

Optional: `gsplat` (for 3DGS backend, needs CUDA GPU), COLMAP (for reconstruction).

### 6.2 Running the Viewer

```bash
python scripts/serve.py
# Open http://localhost:8000/viewer/
```

Drag any `.json` or `.mmi` file onto the viewer, or select from the sample dropdown.

Controls:
- **Mouse drag**: orbit
- **Scroll**: zoom
- **Space**: play/pause
- **← →**: step frame
- **Timeline slider**: scrub
- **Layer checkboxes**: toggle visibility
- **Slice controls**: clip geometry along X/Y/Z axis

### 6.3 Dimensional Lifting (single-view)

**Text-only** (transcript → template match):
```bash
python scripts/etu_comprehend.py \
  --transcript lecture.vtt \
  --out data/samples/auto.json
```

**Hybrid** (video + transcript → vision eye + reasoning brain):
```bash
python scripts/etu_comprehend.py \
  --video my_animation.mp4 \
  --transcript narration.vtt \
  --vision-provider gemini \
  --out data/samples/auto.json
```

**Universal engine** (any video → general lift, no template needed):
```bash
python scripts/etu_understand.py \
  --video any_animation.mp4 \
  --vision-provider gemini \
  --mode auto \
  --out data/samples/auto.json
```

Self-test (no API keys needed):
```bash
python scripts/etu_understand.py --self-test
python scripts/etu_comprehend.py --self-test
```

### 6.4 Reconstruction Pipeline (multi-view)

**Full pipeline run:**
```bash
python scripts/run_pipeline.py \
  --backend synthetic \
  --out data/samples/recon.json \
  cam0.mp4 cam1.mp4 cam2.mp4
```

**Backend selection:**
```bash
# CPU baseline
python scripts/run_pipeline.py --backend colmap cam0.mp4 cam1.mp4

# GPU: 3D Gaussian Splatting
python scripts/run_pipeline.py --backend 3dgs cam0.mp4 cam1.mp4 cam2.mp4

# Fallback (no real data)
python scripts/run_pipeline.py --backend synthetic cam0.mp4
```

### 6.5 Format Conversion

```bash
# mmi-lite → mmi-git
python scripts/mmi_convert.py data/samples/fourier_stack.json \
  --out data/samples/fourier_stack.mmi
```

### 6.6 Generating Synthetic Test Data

```python
from mmi.stages.encode_git import encode_synthetic

scene = encode_synthetic(n_frames=60, n_points=1000, n_parts=4)
scene.save("test_scene.mmi")
```

### 6.7 API Keys

Set as environment variables:
- `DEEPSEEK_API_KEY` — text reasoning (classification, template params)
- `GEMINI_API_KEY` — vision (frame description, FeatureGraph extraction)
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` — alternative vision providers

---

## 7. File Structure

```
ana_eng_ver2/
├── mmi/                          # Python library
│   ├── formats/
│   │   ├── mmi_scene.py          # mmi-lite format (Scene, Keyframe, geometries)
│   │   └── mmi_git.py            # mmi-git format (base + commits + keyframes)
│   ├── etu/                      # Dimensional lifting engine
│   │   ├── spec.py               # LessonSpec contract
│   │   ├── synthesize.py         # Template dispatch
│   │   ├── router.py             # Universal entry (template upgrade + fallback)
│   │   ├── colormap.py           # Colormap utilities
│   │   ├── comprehend/           # Vision + reasoning
│   │   │   ├── catalog.py        # Closed-set template catalog
│   │   │   ├── classify.py       # Text → LessonSpec or abstain
│   │   │   ├── llm.py            # Provider-neutral LLM interface
│   │   │   ├── vision.py         # Frame description (Gemini eye)
│   │   │   └── evidence.py       # Transcript/OCR/hint aggregation
│   │   ├── understand/           # Universal engine
│   │   │   ├── schema.py         # FeatureGraph data model
│   │   │   ├── extract.py        # Frames → FeatureGraph (vision)
│   │   │   ├── lift.py           # FeatureGraph → 3D scene (general)
│   │   │   ├── identity.py       # Object ID reconciliation (union-find)
│   │   │   └── sampling.py       # Change-driven frame sampling
│   │   └── templates/            # 7 math visualization templates
│   │       ├── fourier_stack.py
│   │       ├── complex_surface.py
│   │       ├── graph_surface.py
│   │       ├── taylor_series.py
│   │       ├── vector_field.py
│   │       ├── linear_transform.py
│   │       └── parametric_surface.py
│   ├── stages/                   # Reconstruction pipeline stages
│   │   ├── ingest.py             # Stage 1: video → frames (multi-view)
│   │   ├── keyframes.py          # Stage 2: frame selection
│   │   ├── reconstruct.py        # Stage 3: COLMAP / 3DGS / dyn-NeRF
│   │   ├── segment.py            # Stage 4: color/part segmentation
│   │   ├── track.py              # Stage 5: Kabsch rigid tracking
│   │   ├── assemble.py           # Stage 6: reconstruction → mmi-lite
│   │   └── encode_git.py         # Stage 7: reconstruction → mmi-git
│   └── pipeline/
│       ├── config.py             # PipelineConfig dataclass
│       └── pipeline.py           # 6-stage orchestrator
├── scripts/
│   ├── etu_comprehend.py         # Comprehend CLI (template match)
│   ├── etu_understand.py         # Universal engine CLI (general lift)
│   ├── etu_make.py               # Generate sample scenes
│   ├── mmi_validate.py           # Validate mmi-lite JSON
│   ├── mmi_convert.py            # mmi-lite ↔ mmi-git converter
│   ├── run_pipeline.py           # Full reconstruction pipeline CLI
│   └── serve.py                  # HTTP server for viewer
├── viewer/
│   ├── index.html                # Viewer UI
│   └── main.js                   # Three.js renderer + mmi-git/mmi-lite support
├── data/
│   ├── samples/                  # Sample scene files (.json + .mmi)
│   └── work/                     # Pipeline scratch directory
├── tests/
│   └── test_mmi_git.py           # mmi-git unit tests
└── docs/
    └── plans/                    # Implementation plans
```

---

## 8. Key Design Decisions

### 8.1 Why "dimensional lifting" instead of NeRF for single-view

A single 2D animation of a Fourier series has no hidden depth information. No amount of neural rendering can recover what isn't there. Instead of hallucinating depth, the system *understands* the domain (via LLM) and *re-authors* a mathematically correct 3D representation. The template catalog is the knowledge base.

### 8.2 Why git-like deltas for storage

Full per-frame snapshots are O(N) storage. A 1000-frame point cloud at 5000 points is ~45 MB as snapshots, ~83 KB as base + commits. The trade is compute at playback time, but with periodic keyframes the max work per frame is bounded to O(30 matrix multiplications).

### 8.3 Why whole-scene commits (not per-part)

The user's partner handles time orchestration — they need to see and adjust the full state at any timepoint. Whole-scene commits make each timepoint a self-contained adjustment point. Git's principle: each commit is atomic and meaningful.

### 8.4 Why both pipelines coexist

They solve fundamentally different problems:
- **Dimensional lifting**: single camera, flat content, no real depth → understand + re-author
- **Reconstruction**: multiple cameras, real-world process, true depth → photogrammetry + neural rendering

Both produce the same output format. The viewer doesn't care which pipeline made the file.

---

## 9. Future Directions

### 9.1 Template Catalog Expansion

The current 7 math templates cover Fourier series, complex surfaces, graph surfaces, Taylor series, vector fields, linear transforms, and parametric surfaces. Natural extensions:

- **Chemistry**: molecular structures, reaction pathways, bond formation/breaking
- **Anatomy**: organ systems, surgical procedures, cellular processes
- **Physics**: phase portraits, field lines, wave propagation
- **Engineering**: mechanism kinematics, fluid dynamics, structural analysis

Each template is a `build(params) → Scene` function with validated parameter ranges. Adding one requires ~100–200 lines of Python.

### 9.2 Dynamic NeRF (4DGS) Backend

The `dyn-nerf` backend in `reconstruct.py` is stubbed. A full implementation would train a single 4D Gaussian Splatting model capturing the entire temporal sequence, rather than per-window static models. This handles highly dynamic scenes (explosions, fluid flow, deformations) where per-window reconstruction fails.

### 9.3 Person B .mmi Compiler

The mmi-lite format was designed as an interim representation. Person B's `.mmi` compiler would take the JSON scene description and produce a compiled binary format optimized for streaming playback — quantization, delta encoding of vertex data, binary matrices, LOD (level of detail) for distant objects.

### 9.4 Streaming Playback

For long processes (hours of footage), mmi-git supports streaming: load the base + first N commits, start playback, fetch remaining commits asynchronously. The keyframe structure already enables partial loading.

### 9.5 SAM-based Segmentation

The `segmenter="sam"` path in `segment.py` is stubbed. Segment Anything in 3D would use lifted 2D masks across views for semantic part segmentation — distinguishing "reagent A" from "reagent B" by appearance, not just color.

### 9.6 Learned Deformation Fields

The `track_method="deform"` path in `track.py` is stubbed. Replacing rigid Kabsch tracking with learned deformation fields would handle non-rigid transformations (stretching, bending, morphing) — critical for biological and soft-body processes.

### 9.7 WebGPU Viewer

The current Three.js viewer uses WebGL. A WebGPU backend would enable larger point clouds (millions of points), real-time Gaussian splat rendering, and compute-shader-accelerated matrix accumulation for mmi-git playback.

### 9.8 Collaborative Time Orchestration

The whole-scene commit model was designed for a partner who handles timeline editing. A collaborative editor could allow both:
- **Reconstruction author**: generates the base + commit chain
- **Time orchestrator**: inserts, removes, reorders, or adjusts individual commits
- Changes merge via the mmi-git format's named-part addressing

---

## 10. Contributing

1. All Python code lives under `mmi/`. Tests under `tests/`.
2. Run `python tests/test_mmi_git.py` before committing format changes.
3. Both pipelines should produce valid mmi-lite or mmi-git output — run `scene.validate()` to check.
4. The viewer works with no build step — just refresh the browser.

---

*Document version: 2026-07-29. Last updated with mmi-git v0.1 and reconstruction pipeline implementation.*
