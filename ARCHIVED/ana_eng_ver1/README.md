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
> here is the strawman they target (see [`docs/FILE_FORMAT.md`](docs/FILE_FORMAT.md)).

## The ETU pipeline

```
 2D video ──comprehend──► LessonSpec ──author──► mmi-lite Scene ──► interactive 3D viewer
           (vision model,   (concept +   (parametric
            FUTURE)          params)      templates, NOW)
```

We build **template-first**: a library of parametric math templates that lift a
named concept into 3D *today*, with the video-understanding step plugged in later
behind the same `LessonSpec` seam (`mmi/etu/spec.py`). Nothing downstream changes
when comprehension is added.

## What works today

- **Seven math templates** (`mmi/etu/templates/`), each a different 2D→3D win:
  | concept | 2D you'd see on a slide | 3D lift ETU adds |
  | --- | --- | --- |
  | `complex_surface` | domain-coloring of `f(z)` | morphs up into the `|f(z)|` landscape — poles/zeros revealed |
  | `graph_surface` | heatmap of `f(x,y)` | morphs flat heatmap into the actual surface |
  | `fourier_stack` | a square wave | decomposes it into sine harmonics stacked along a new depth axis, with a converging running sum |
  | `taylor_series` | f(x) + approximations | stacks each added term by degree; running approximation morphs toward the target |
  | `vector_field` | flat arrow diagram | fills 3D space with arrows (rotation/source/saddle/…) you can orbit |
  | `linear_transform` | a matrix of numbers | a lattice + basis vectors morph from identity to the matrix; determinant = volume scaling |
  | `parametric_surface` | x(u,v),y(u,v),z(u,v) | the flat (u,v) domain morphs into the 3D shape (torus/sphere/helicoid/Möbius) |
- **Interactive viewer** — orbit, scrub time, slice, toggle layers, scene picker.
  Supports morphing `line`/`surface` geometry (vertex-interpolated animation).
- **Format + synthesis seam** — `mmi-lite` scene schema and `LessonSpec` → Scene
  authoring, all validated.

## Quickstart

Deploy and try it yourself in five steps. Steps 1–2 need **no API keys**; steps
3–4 turn *your own* 2D video into a 3D scene and need keys.

### 0. Prerequisites
- Python 3.10+ (tested on 3.13)
- `ffmpeg` — only needed to extract frames from a video: `brew install ffmpeg`
- Install deps:
  ```bash
  cd mmi-prototype
  pip install -r requirements.txt        # numpy, Pillow (matplotlib only if you generate test clips)
  ```

### 1. See it now — prebuilt sample scenes (no keys)
```bash
python scripts/etu_make.py --all         # generate the 7 math sample scenes
python scripts/serve.py                  # opens http://localhost:8000/viewer/
```
Use the **Scene** dropdown (top-right) to switch scenes; drag to orbit, `Space`
to play, the slider to scrub. (Open via `serve.py`, not `file://` — browsers
block the sample fetch on `file://`; there you must drag a `.json` in.)

### 2. Sanity-check the engine offline (no keys)
```bash
python scripts/etu_comprehend.py --self-test   # closed-set classify path
python scripts/etu_understand.py  --self-test   # universal engine (extract→route→lift)
```
Both should print `self-test: PASS`.

### 3. Set your API keys (for the live engine)
```bash
export DEEPSEEK_API_KEY=sk-...     # the "brain": routes to a template when one fits
export GEMINI_API_KEY=...          # the "eye": extracts objects+changes from frames
```
(Vision alternatives: `OPENAI_API_KEY` + `--vision-provider openai`, or
`OPENROUTER_API_KEY` + `--vision-provider openrouter`.)

### 4. Turn YOUR 2D video into a 3D scene (the universal engine)
```bash
python scripts/etu_understand.py --video myclip.mp4 \
    --vision-provider gemini --mode auto --out data/samples/auto.json
```
- `--mode auto` → upgrade to a correct math template if it confidently fits, else
  the general lift. `--mode general` forces the general lift; `--mode template`
  only templates.
- No video file? Pass a folder of frames instead: `--frames path/to/pngs`.
- **View the result:** with `serve.py` running, open the viewer and use
  **Load file…** (or drag `data/samples/auto.json` onto the window).

### 5. (Optional) Author math scenes directly / from a transcript
```bash
python scripts/etu_make.py complex_surface --param func=1/z      # hand-authored
python scripts/etu_make.py fourier_stack   --param harmonics=12
python scripts/etu_comprehend.py --transcript lecture.vtt --out data/samples/auto.json   # text-only, DeepSeek
```

### Troubleshooting (issues seen during testing)
| Symptom | Fix |
| --- | --- |
| Gemini `429 ... limit: 0` for a model | that model has no quota on your key; use the default `gemini-2.5-flash` or `--vision-model gemini-flash-latest` |
| Gemini `400 Please pass a valid API key` | key is invalid/rotated — paste a fresh one |
| `missing API key — set DEEPSEEK_API_KEY` | `export` the var in the *same* shell before running |
| `--video` errors with "Neither OpenCV nor ffmpeg" | `brew install ffmpeg` |
| Viewer blank / "couldn't fetch sample" | you opened `index.html` via `file://` — run `scripts/serve.py` and use the `localhost` URL, or drag a `.json` in |
| Scene slow to load | lower resolution: e.g. `--param n=28`, or fewer `--max-images` for vision |

### What to report back (known soft spots — your feedback targets)
Please tell me where these help or break on real clips:
1. **Object lifetime** — in the *general* lift, objects that disappear/merge are
   not yet hidden after their last frame (they hold their last position).
2. **Depth is approximate** — 2D→true-spatial-depth is ambiguous; orbiting shows
   an inferred depth, motion + time are exact.
3. **Vision extraction quality** — the eye is non-deterministic; timelines can be
   coarse or miss fast events. Note the clip + what it got wrong.
4. **Surface shading** is flat (no per-frame lighting) — readability feedback welcome.

Note bugs as `file:line` or the command you ran + output, and I'll fix/tune.

## Viewer controls

| Action | Control |
| --- | --- |
| Orbit / zoom / pan | drag / scroll / right-drag |
| Play / pause · step | `Space` · `←`/`→` |
| Scrub time | timeline slider |
| Switch scene | **Scene** dropdown |
| Toggle parts | **Layers** checkboxes |
| Cutaway | **Slice** axis + position |
| Load your own | drag a `.json` in, or **Load file…** |

## Layout

```
mmi/
  etu/
    spec.py              # LessonSpec — the comprehend↔author seam
    synthesize.py        # LessonSpec -> Scene (dispatch to a template)
    templates/           # complex_surface, graph_surface, fourier_stack
    colormap.py
  formats/mmi_scene.py   # mmi-lite schema (box/pointcloud/line/surface + morph)
  pipeline/, stages/     # legacy 3D-reconstruction path (for real multi-view capture)
viewer/                  # Three.js interactive viewer
scripts/                 # etu_make, serve, gen_sample, run_pipeline
docs/                    # ARCHITECTURE, ROADMAP, FILE_FORMAT
```

> The `pipeline/` + `stages/` reconstruction code is **parked, not deleted** — it
> only applies if you later want to ingest *real multi-view footage* of a physical
> 3D process. ETU's path is `etu/`. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Comprehend (E3) — video → LessonSpec, closed-set via DeepSeek

The comprehension stage turns a 2D video into a `LessonSpec` and authors the
scene, end to end:

```bash
export DEEPSEEK_API_KEY=sk-...        # your key

# classify a transcript into one template (or abstain) and build the 3D scene
python scripts/etu_comprehend.py --transcript data/samples/sample_transcript_fourier.vtt \
    --out data/samples/auto.json
# -> concept: fourier_stack, then authors + saves the scene; drag auto.json into the viewer

# no key needed — verify the whole closed-set path offline:
python scripts/etu_comprehend.py --self-test
```

**Hybrid (vision eye + DeepSeek brain).** DeepSeek's API is **text-only**, so to
use the pixels we add a vision model that *describes* the frames; that description
joins the transcript as evidence for DeepSeek's closed-set decision. The eye only
describes — DeepSeek still decides — so the low-risk design is preserved.

```bash
export DEEPSEEK_API_KEY=sk-...        # the brain (decides)
export GEMINI_API_KEY=...             # the eye (describes); or OPENAI_/OPENROUTER_

# extract keyframes from the mp4, describe them, then classify
python scripts/etu_comprehend.py --video clip.mp4 --vision-provider gemini \
    --transcript lecture.vtt --out data/samples/auto.json
```

Vision providers (all OpenAI-compatible): `gemini` (cheap, strong on images),
`openai`, `openrouter` (Qwen-VL etc.). Pick whichever key you have; override the
model with `--vision-model`. Without `--vision-provider` it runs **text-only**
(transcript + optional `--ocr`), which is all you need while iterating on DeepSeek.

**Why closed-set:** the model may only choose one catalog concept (or `"none"`)
and fill its declared params, which are then validated and clamped
(`mmi/etu/comprehend/catalog.py`). It cannot invent geometry, and it abstains
when nothing fits — the riskiest part (correct 3D authoring) stays owned by the
template library.

## Universal engine — any 2D animation → 3D/4D (general, not just templates)

The closed-set templates cover known domains with *correct* 3D. For everything
else, the **general engine** extracts a domain-agnostic **FeatureGraph** (the
objects, their features, and how they change over time) from any animation and
**lifts** it to a 3D/4D scene — objects become 3D primitives that move over time
and leave orbitable trajectory trails.

```
video → keyframes → [vision] FeatureGraph ─┬─ template upgrade (if it confidently fits) → correct scene
   (objects + features + changes, domain-agnostic) └─ general lift (otherwise) → approximate scene
```

```bash
# auto: extract → upgrade to a template if it fits, else general lift
python scripts/etu_understand.py --video clip.mp4 --vision-provider gemini --mode auto

# offline self-test of all three paths (no keys)
python scripts/etu_understand.py --self-test
```

The **router** (`mmi/etu/router.py`) gives universal coverage — *everything* gets
at least the general lift — while known domains get the reliable template.

**Honest limit:** lifting flat 2D to *true spatial* depth is ambiguous (a moving
circle could be a sphere or a disc — the pixels don't say). The general lift
infers a plausible depth from occlusion/shape and keeps the faithful axes —
object **motion** and **time** — exact. It's an honest approximation, not a
fake-correct reconstruction; templates give correctness where they apply.
