# Project ETU — Easier-To-Understand

Take a flat **2D academic explainer** (a 3blue1brown-style math video, a medical
process animation) and *promote it into a 3D interactive scene*, so a concept is
easier for the brain to grasp. The viewer lets you see the idea from any angle
and scrub through it in time.

> **What ETU is:** dimensional *lifting by understanding + re-authoring* — watch
> the 2D lesson, understand the concept, and **generate** a new 3D scene that
> re-explains it. The input video is a *spec*, not raw geometry to reconstruct.
> (This is different from 3D reconstruction/NeRF, which needs multi-view footage
> of a real object — a flat animation has no hidden 3D to recover.)

> **Team:** this repo is **Person A** (the analysis → 3D-scene model). Person B
> owns the `.mmi` file format + a `.txt`→`.mmi` compiler; the `mmi-lite` JSON
> here is the strawman they target.

## Architecture

**One reasoning model, many tools. No separate vision LLM.**

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

Vision understanding comes from **deterministic CV modules** — optical flow,
edge detection, contour finding, color clustering — that run locally with
OpenCV. No vision API keys, no network calls, no LLM tokens spent describing
pixels. A single reasoning model (DeepSeek) interprets the structured CV
output, labels objects, and decides template vs general lift.

For multi-view video of real 3D scenes, the reconstruction pipeline uses
COLMAP, 3DGS, and NeRF backends — the same reasoning model orchestrates them.

Both pipelines converge on the same Three.js viewer, which auto-detects
format (mmi-lite JSON or mmi-git `.mmi`).

## What works today

### Seven math templates (`mmi/etu/templates/`)

| concept | 2D you'd see on a slide | 3D lift ETU adds |
| --- | --- | --- |
| `complex_surface` | domain-coloring of `f(z)` | morphs up into the `|f(z)|` landscape — poles/zeros revealed |
| `graph_surface` | heatmap of `f(x,y)` | morphs flat heatmap into the actual surface |
| `fourier_stack` | a square wave | decomposes it into sine harmonics stacked along a new depth axis, with a converging running sum |
| `taylor_series` | f(x) + approximations | stacks each added term by degree; running approximation morphs toward the target |
| `vector_field` | flat arrow diagram | fills 3D space with arrows (rotation/source/saddle/…) you can orbit |
| `linear_transform` | a matrix of numbers | a lattice + basis vectors morph from identity to the matrix; determinant = volume scaling |
| `parametric_surface` | x(u,v),y(u,v),z(u,v) | the flat (u,v) domain morphs into the 3D shape (torus/sphere/helicoid/Möbius) |

### Universal engine — any 2D animation → 3D/4D

Give `scripts/etu_understand.py` *any* 2D explainer/simulator clip. CV modules
extract a domain-agnostic **FeatureGraph** (objects + how they change) from the
frames — no vision LLM needed. The reasoning model then either upgrades to a
matching template (correct, high-quality) or lifts generically (works on
anything, honest about depth).

Features:
- **Change-driven frame sampling** — samples where the animation *changes*, not
  on a fixed clock (skips static stretches, catches the moment of change)
- **Object-identity reconciliation** — stitches frame-to-frame ID drift
  (split/duplicate tracks) from CV object detection
- **Object lifetime** — objects fade in when born and fade out when they
  merge/leave (keyframe `opacity`), instead of lingering

### Two output formats, one viewer

- **mmi-lite** (JSON) — per-frame keyframe snapshots, human-readable
- **mmi-git** (`.mmi`) — git-inspired delta storage: base scene + chain of
  4×4 transform matrices, ~54:1 compression, O(1) random access via periodic
  keyframes. 4 geometry types: PointCloud, Box, Surface, Line

### Interactive viewer

Orbit, scrub time, slice, toggle layers, scene picker. Morphing geometry
**and** interpolated pose (position lerp + quaternion slerp) so sparse
*event* keyframes glide rather than snap.

## Quickstart

This is the full path: install → verify offline → set one key → turn a 2D
video into a 3D scene → view it. Steps 0–2 need **no API key**; step 3
onward needs a reasoning key for template matching.

### 0. Install (one time)

```bash
cd ana_eng_ver2
python3 -m pip install -r requirements.txt   # numpy, Pillow, opencv-python
```
Requires **Python 3.10+** and **ffmpeg** on your PATH (for video frame extraction).

### 1. Verify offline (no key)

```bash
python3 scripts/etu_understand.py --self-test    # 6 tests: general lift, template routing, fallback, CV module, identity, sampling
python3 scripts/etu_comprehend.py --self-test    # closed-set template classifier
```
Both must print `self-test: PASS`.

### 2. See prebuilt scenes in the viewer (no key)

```bash
python3 scripts/etu_make.py --all     # build the 7 math sample scenes
python3 scripts/serve.py              # serves http://localhost:8000/viewer/
```
Open **http://localhost:8000/viewer/** (use the server, *not* `file://`). Pick a
scene from the **Scene** dropdown; drag to orbit, `Space` to play, slider to scrub.

### 3. Set your reasoning API key

```bash
export DEEPSEEK_API_KEY=sk-...     # the sole LLM — classifies, labels, decides template vs general
```
That's the only key you need. CV analysis runs locally with OpenCV — no vision
API keys, no Gemini, no network calls for feature extraction.

### 4. Get a video — yours, or generate a test clip

Use your own 2D animation, **or** make one:
```bash
python3 scripts/make_test_clip.py --out data/work/orbit.mp4   # a 2D orbit animation
```

### 5. Analyze the video → 3D scene

```bash
python3 scripts/etu_understand.py \
    --video data/work/orbit.mp4 \
    --mode general \
    --out data/samples/orbit_auto.json
```
What you'll see printed: how many frames were extracted, objects detected by CV,
and the saved scene path.

- `--mode general` always lifts generically (works on anything, no key needed)
- `--mode auto` upgrades to a correct math template if the clip confidently
  matches one (needs `DEEPSEEK_API_KEY`)
- `--mode template` only templates (abstains if no match)
- `--max-cv-images N` (default 8) — max frames for CV analysis; raise for
  fast/complex motion
- `--transcript file.vtt` — optional narration text as evidence for the
  reasoning model

No video, only images? Use `--frames path/to/pngs` instead of `--video`.

### 6. Validate and view

```bash
python3 scripts/mmi_validate.py data/samples/orbit_auto.json   # contract check (should be ✓)
```
With `scripts/serve.py` running, open the viewer, **hard-reload** (Cmd/Ctrl-Shift-R),
and either pick the scene from the dropdown or use **Load file…** / drag the
`.json` onto the window.

## Reconstruction pipeline

For multi-view synchronized video of real 3D scenes:

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

Pipeline stages: ingest (multi-view) → keyframes → reconstruct (COLMAP/3DGS/NeRF)
→ segment → track (Kabsch) → encode_git.

## Viewer controls

| Action | Control |
| --- | --- |
| Orbit / zoom / pan | drag / scroll / right-drag |
| Play / pause · step | `Space` · `←`/`→` |
| Scrub time | timeline slider |
| Switch scene | **Scene** dropdown |
| Toggle parts | **Layers** checkboxes |
| Cutaway | **Slice** axis + position |
| Load your own | drag a `.json` or `.mmi` in, or **Load file…** |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `self-test` import error | run from `ana_eng_ver2/`, `pip install -r requirements.txt` |
| `--video` errors "Neither OpenCV nor ffmpeg" | install ffmpeg (must be on PATH) |
| only 1–2 objects detected, motion lost | already handled — CV samples by change; if it persists, raise `--max-cv-images` |
| `missing API key — set DEEPSEEK_API_KEY` | export it in the *same* shell; only needed for `--mode auto`/`template` |
| Viewer all black / blank | use `serve.py` localhost URL, not `file://`; hard-reload |
| Viewer "couldn't fetch sample" | run `scripts/serve.py`, or drag a `.json` in |
| Scene plays too fast | use **Speed** control (0.25×) and scrub the slider |
| CV module fails with "opencv-python required" | `pip install opencv-python` |

## Layout

```
ana_eng_ver2/
├── mmi/
│   ├── formats/
│   │   ├── mmi_scene.py      # mmi-lite format (Scene, SceneObject, Keyframe, 4 geometry types)
│   │   └── mmi_git.py        # mmi-git format (MmiGitScene, PartSpec, Commit, KeyFrame)
│   ├── etu/                   # Dimensional lifting engine
│   │   ├── vision/            # CV analysis — deterministic, no LLM
│   │   │   ├── analysis.py    #   optical flow, edges, contours, color clustering
│   │   │   └── extract.py     #   FrameAnalysis → FeatureGraph (object tracking)
│   │   ├── comprehend/        # Reasoning model classification (sole LLM)
│   │   │   ├── classify.py    #   text evidence → LessonSpec (closed-set, abstaining)
│   │   │   ├── catalog.py     #   template catalog (7 concepts + params)
│   │   │   ├── llm.py         #   OpenAI-compatible chat client
│   │   │   └── evidence.py    #   transcript/hint/OCR gathering
│   │   ├── understand/        # FeatureGraph extraction + 3D lifting
│   │   │   ├── schema.py      #   FeatureGraph (domain-agnostic objects+changes)
│   │   │   ├── extract.py     #   frames → FeatureGraph (CV-based, no vision LLM)
│   │   │   ├── sampling.py    #   change-driven frame selection
│   │   │   ├── identity.py    #   reconcile CV object ID drift
│   │   │   └── lift.py        #   FeatureGraph → 3D/4D Scene (event keyframes + lifetime)
│   │   ├── templates/         # 7 math templates
│   │   ├── router.py          # Template upgrade vs general fallback
│   │   ├── spec.py            # LessonSpec — comprehend↔author seam
│   │   └── synthesize.py      # LessonSpec → Scene (dispatch to template)
│   ├── stages/                # Reconstruction pipeline
│   │   ├── ingest.py          # Multi-view video → frames
│   │   ├── keyframes.py       # Content-based frame selection
│   │   ├── reconstruct.py     # COLMAP / 3DGS / dyn-nerf backends
│   │   ├── segment.py         # Color clustering / SAM segmentation
│   │   ├── track.py           # Kabsch rigid tracking
│   │   └── encode_git.py      # Reconstruction → mmi-git encoder
│   ├── pipeline/              # Pipeline orchestrator
│   └── synth/                 # Synthetic scene generators (rubiks.py)
├── viewer/
│   ├── index.html             # Viewer HTML + CSS
│   └── main.js                # Three.js viewer (834 lines, all rendering logic)
├── scripts/
│   ├── etu_make.py            # Generate template sample scenes
│   ├── etu_understand.py      # Universal engine CLI (CV + reasoning)
│   ├── etu_comprehend.py      # Comprehension test (reasoning model only)
│   ├── mmi_convert.py         # mmi-lite ↔ mmi-git converter
│   ├── mmi_validate.py        # Format validator
│   ├── run_pipeline.py        # Reconstruction pipeline CLI
│   └── serve.py               # HTTP server for viewer
├── tests/
│   └── test_mmi_git.py        # 15 unit tests for mmi-git format
├── data/samples/              # Sample scene files
├── WIKI.md                    # Full technical documentation
└── requirements.txt
```

## Honest limits (what to report back)

1. **Depth is approximate** — 2D→true-spatial depth is ambiguous; orbiting
   shows an *inferred* depth, while object **motion** and **time** are faithful.
2. **CV object detection quality** — deterministic CV is fast and free but
   can miss small/fast/overlapping objects. The reasoning model labels
   whatever CV finds; report clips where objects were missed or mis-tracked.
3. **Keyframe spacing is uniform**, not yet proportional to real elapsed
   time between events.
4. **Surface shading** is flat (no per-frame lighting) — readability
   feedback welcome.

## Key design decisions

See [`WIKI.md`](WIKI.md) for the full rationale, but the short version:

1. **Pivot from reconstruction to dimensional lifting** (June 28) — the input
   is 2D animations, there's no hidden 3D to reconstruct.
2. **Single reasoning model, no vision LLM** (August 4) — CV modules extract
   visual features deterministically; one reasoning model orchestrates
   everything.
3. **Whole-scene commits** (Option B) — each mmi-git commit contains transforms
   for ALL parts, for collaborative time orchestration.
4. **Matrix-chain deltas** — spatial changes stored as matrix multiplications,
   elegant and mathematically clean.
5. **Template-first + universal fallback** — correct templates for known
   domains, general lift for everything else.
