# Project ETU — WIKI

**Last Updated:** 2026-08-14
**Location:** ~/Documents/progproj/projute/ana_eng_ver2/

## 1. Architecture Overview

ETU converts 2D process animations/videos into interactive 4D (3D + time) scenes
viewable from any angle at any time point.

**Single reasoning model + CV/3D tools — no separate vision LLM.**

The architecture uses ONE reasoning model (DeepSeek) that orchestrates many
tools: deterministic CV modules (optical flow, edge detection, contour finding,
color segmentation) for visual feature extraction, 3D reconstruction modules
(COLMAP, 3DGS) for geometric reconstruction, and template generators for
known domains. No separate vision LLM — all visual understanding comes from
CV tools feeding structured data to the reasoning model.

**Two pipelines converge on one viewer:**

```
                    ┌── Dimensional Lifting ───────────────────┐
  Video / Text ──→  │  CV analysis → FeatureGraph → Reasoning  │──→ mmi-lite JSON ──┐
                    │  model (DeepSeek) → template/general lift│                    │
                    └──────────────────────────────────────────┘                    │
                                                                                     ├──→ Three.js Viewer
                    ┌── Reconstruction ────────────────────────┐                    │
  Multi-view Video →│  (3DGS / COLMAP / NeRF) → Reasoning     │──→ mmi-git .mmi ──┘
                    │  model → format encoder                  │
                    └──────────────────────────────────────────┘
```

## 2. mmi-git Format Specification (v0.2)

Git-inspired delta storage for 4D processes. Instead of per-frame snapshots,
stores a base scene + a chain of 4×4 homogeneous transform matrices.

### 2.1 Format Header

```json
{
  "format": "mmi-git",
  "version": "0.2",
  "meta": {
    "title": "Scene name",
    "fps": 30,
    "duration_frames": 120,
    "source": "reconstruction" | "converted:..." | "synthetic",
    "coordinate_system": "right-handed-y-up",
    "events": [{"t": 0, "label": "Start"}]
  }
}
```

### 2.2 Geometry Types (v0.2)

Each part carries a `geometry` block specifying one of four kinds:

**Pointcloud** (legacy + explicit)
```json
{
  "id": "part_00",
  "label": "Blue ball",
  "geometry": {"kind": "pointcloud", "point_size": 0.03},
  "point_indices": [0, 1, 2, ...],
  "color": "#8ab4ff"
}
```
Point indices reference the global `base.points` array.

**Box** (crisp cubes with colored faces)
```json
{
  "id": "cubie_00",
  "label": "Corner cubie",
  "geometry": {
    "kind": "box",
    "size": [0.94, 0.94, 0.94],
    "face_colors": {
      "px": "#B71234", "nx": "#FF5800",
      "py": "#FFFFFF", "ny": "#FFD500",
      "pz": "#009B48", "nz": "#0046AD"
    }
  }
}
```
Self-contained — no base_points reference needed.

**Surface** (grid mesh with vertex colors)
```json
{
  "id": "waveform",
  "label": "Complex surface z^3-1",
  "geometry": {
    "kind": "surface",
    "rows": 44, "cols": 44,
    "positions": [x0,y0,z0, ...],
    "colors": [r,g,b, ...],
    "opacity": 1.0,
    "wireframe": false
  }
}
```

**Line** (polyline)
```json
{
  "id": "curve",
  "label": "Harmonic curve",
  "geometry": {
    "kind": "line",
    "positions": [x0,y0,z0, ...],
    "color": "#5b8cff",
    "width": 2.0
  }
}
```

### 2.3 Commits & Keyframes

- **Commits**: each frame records a whole-scene transform (one 4×4 matrix per part).
  Matrices are row-major, 16 floats, encoding the delta from previous frame.
- **Keyframes**: periodic full snapshots every ~30 frames for O(1) random access.
- **Compression**: ~54:1 for 100-frame scenes with 5000 points.

### 2.4 Design: Matrix Transform Dispatch

| Geometry Kind | Transform Method |
|---|---|
| pointcloud | Per-vertex matrix multiplication |
| box, surface, line | Accumulate matrices → decompose to position/quaternion/scale → apply to mesh |

Non-pointcloud geometry stays crisp — no vertex deformation. The commit chain
handles motion identically for all types; only the viewer dispatch differs.

## 3. Technical Stack

| Layer | Technology |
|---|---|
| Format (Python) | dataclasses + numpy, JSON serialization |
| CV Analysis (vision) | OpenCV (optical flow, edge detection, contours, color clustering) — deterministic, no LLM |
| Reasoning Model | DeepSeek (sole LLM — classifies, labels, decides template vs general) |
| Reconstruction | COLMAP, gsplat (3DGS), OpenCV, numpy |
| Tracking | Kabsch (SVD rigid alignment), k-means segmentation |
| Viewer | Three.js r161, ES modules, no build step |
| Server | Python stdlib http.server |

## 4. CLI Usage

### API Key Configuration (per-user, no shell editing)

```bash
# Store each provider's key once — interactive, hidden input:
python scripts/etu_config.py set deepseek
# Non-interactive:
python scripts/etu_config.py set deepseek --key sk-...
# List configured providers (keys redacted):
python scripts/etu_config.py get
# Show config file location:
python scripts/etu_config.py path
```

Key priority when the engine runs: environment variable (e.g. DEEPSEEK_API_KEY)
> `~/.config/etu/config.json` (chmod 600). No ~/.bashrc editing required for a
distributable install.

### Dimensional Lifting Pipeline

```bash
# Generate template scenes
python scripts/etu_make.py --all

# Universal engine (single video → 3D) — CV analysis extracts objects, reasoning model decides
python scripts/etu_understand.py --video data/work/process.mp4 \
    --mode auto --out data/samples/output.json

# Interactive: pause at each stage transition and describe the change in natural language.
# The notes are folded into the reasoning model as extra evidence (it may correct object
# labels/relations) and persisted as HUD events. Enter = let the model guess (auto path).
python scripts/etu_understand.py --video data/work/process.mp4 \
    --mode auto --out data/samples/output.json --interactive

# Comprehension test (reasoning model only — classifies from transcript/hint)
python scripts/etu_comprehend.py --video data/work/fourier.mp4

# Start viewer
python scripts/serve.py
# Open http://localhost:8000/viewer/
```

### Reconstruction Pipeline

```bash
# Full pipeline (synthetic for testing)
python scripts/run_pipeline.py data/work/video.mp4 \
    --backend synthetic --out data/samples/recon.mmi

# With real backends (needs GPU)
python scripts/run_pipeline.py data/work/video.mp4 \
    --backend 3dgs --target-fps 5

# Convert mmi-lite → mmi-git
python scripts/mmi_convert.py data/samples/scene.json \
    --out data/samples/scene.mmi
```

## 5. File Structure

```
ana_eng_ver2/
├── mmi/
│   ├── formats/
│   │   ├── mmi_scene.py      # mmi-lite format (datalasses, validate, save)
│   │   └── mmi_git.py        # mmi-git format (GitGeometry, PartSpec, Commit,
│   │                          #   MmiGitScene, compute_frame, keyframes)
│   ├── etu/                   # Dimensional lifting engine
│   │   ├── vision/            # CV analysis (deterministic, no LLM)
│   │   │   ├── analysis.py    # Optical flow, edges, contours, colors
│   │   │   └── extract.py     # FrameAnalysis → FeatureGraph
│   │   ├── comprehend/        # Reasoning model classification (sole LLM)
│   │   │   └── credentials.py # Per-user API-key store (config file)
│   │   ├── understand/        # FeatureGraph extraction + 3D lifting
│   │   ├── templates/        # 7 math templates
│   │   ├── guide.py          # Stage-transition NL guidance (interactive, optional)
│   │   └── router.py         # Template upgrade vs general fallback
│   ├── stages/               # Reconstruction pipeline stages
│   │   ├── ingest.py         # Multi-view video → frames
│   │   ├── keyframes.py      # Frame selection
│   │   ├── reconstruct.py    # COLMAP / 3DGS / dyn-nerf backends
│   │   ├── segment.py        # Color clustering / SAM segmentation
│   │   ├── track.py          # Kabsch rigid tracking
│   │   └── encode_git.py     # Reconstruction → mmi-git encoder
│   ├── pipeline/             # Pipeline orchestrator
│   └── synth/                # Synthetic scene generators (rubiks.py)
├── viewer/
│   ├── index.html            # Viewer HTML + CSS
│   └── main.js               # Three.js viewer (all rendering logic)
├── scripts/
│   ├── etu_make.py           # Generate template sample scenes
│   ├── etu_understand.py     # Universal engine CLI
│   ├── etu_comprehend.py     # Comprehension test CLI
│   ├── etu_config.py         # API-key configuration (per-user config file)
│   ├── mmi_convert.py        # mmi-lite ↔ mmi-git converter
│   ├── run_pipeline.py       # Reconstruction pipeline CLI
│   └── serve.py              # HTTP server for viewer
├── tests/
│   └── test_mmi_git.py       # 15 unit tests for mmi-git format
├── data/
│   └── samples/              # Sample scene files
└── requirements.txt
```

## 6. Key Design Decisions

### 6.1 Pivot from Reconstruction to Dimensional Lifting (June 28)
The original plan was pure 3D reconstruction (3DGS/NeRF). But the actual input
is 2D animations — there IS no hidden 3D to reconstruct. The pivot to
"understand + re-author" was the critical architectural decision.

### 6.2 Two Pipelines, One Viewer (July 29)
Dimensional lifting (single-view, understand + re-author) and reconstruction
(multi-view, photogrammetry + neural rendering) solve different problems but
converge on the same output ecosystem. The viewer renders both formats.

### 6.3 Whole-Scene Commits (Option B)
Each commit contains transforms for ALL parts at that timepoint — chosen for
collaborative time orchestration: the partner can see/adjust full state at
any point.

### 6.4 Rich Geometry Types (July 30)
mmi-git v0.2 adds box, surface, and line geometry beyond the original
pointcloud-only format. Non-pointcloud parts use mesh-level transforms
(position/quaternion/scale) instead of per-vertex matrix multiplication,
keeping geometry crisp through the commit chain.

### 6.5 Matrix-Chain Deltas, Not Raw Geometry Diffs
The user's key insight: "just like linear matrix transformation, you apply
one vector to the matrix and it changes." Spatial changes stored as matrix
multiplications — elegant and mathematically clean.

### 6.6 Single Reasoning Model, No Vision LLM (August 4)
The original architecture used two LLMs: Gemini (vision) to describe frames,
DeepSeek (reasoning) to classify. This was wasteful — the reconstruction
pipeline already has CV/3D modules (optical flow, color segmentation, COLMAP,
3DGS) that can extract visual features deterministically. The vision LLM was
removed. Now a single reasoning model (DeepSeek) orchestrates CV/3D tools:
frames → deterministic CV analysis → structured FeatureGraph → reasoning
model interprets, labels objects, and decides template vs general lift.
This makes every module a tool the reasoning model can call — one brain,
many sensors. No API keys needed for vision, no network calls, no LLM tokens
spent on describing pixels.

## 7. Future Directions

1. **Template catalog expansion** — chemistry, anatomy, phase portraits
2. **Mesh extraction from 3DGS** — SuGaR + Poisson reconstruction for real
   video → crisp box/surface geometry (not just point clouds)
3. **Person B compiler** — partner's side: compiles .mmi into final deliverable
4. **Streaming playback** — progressive loading for large timelines
5. **SAM 3D segmentation** — Segment Anything for per-object masks
6. **Deformation fields** — non-rigid tracking beyond Kabsch
7. **WebGPU viewer** — next-gen browser rendering backend
8. **Collaborative orchestration** — real-time multi-user timeline editing
