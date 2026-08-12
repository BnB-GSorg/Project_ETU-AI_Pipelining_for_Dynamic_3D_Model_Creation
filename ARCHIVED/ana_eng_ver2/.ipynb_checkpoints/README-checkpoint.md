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
- **Universal `.mp4` → 3D engine** (`scripts/etu_understand.py`) — give it *any*
  2D explainer/simulator clip and it extracts a domain-agnostic **FeatureGraph**
  (objects + how they change) with a vision model, then lifts it to an orbitable
  3D/4D scene. Verified live (Gemini) on self-generated orbit and collide/merge
  clips. Includes:
  - **change-driven frame sampling** — samples where the animation *changes*, not
    on a fixed clock (skips static stretches, catches the moment of change);
  - **object-identity reconciliation** — stitches a vision model's frame-to-frame
    ID drift (split/duplicate tracks);
  - **object lifetime** — objects fade in when born and fade out when they
    merge/leave (keyframe `opacity`), instead of lingering.
- **Interactive viewer** — orbit, scrub time, slice, toggle layers, scene picker.
  Morphing `line`/`surface` geometry **and** interpolated pose (position lerp +
  quaternion slerp) so sparse *event* keyframes glide rather than snap.
- **Format + tooling** — `mmi-lite` scene schema, `LessonSpec` → Scene authoring,
  and a zero-dependency reference validator (`scripts/mmi_validate.py`) for the
  format contract. All validated.

## Quickstart — from zero to analyzing a `.mp4`

This is the full path: install → verify offline → set one key → turn a 2D video
into a 3D scene → view it. Steps 0–2 need **no API key**; step 3 onward analyzes a
real clip and needs a vision key.

### 0. Install (one time)
```bash
cd mmi-prototype
python3 -m pip install -r requirements.txt   # numpy, Pillow, matplotlib
brew install ffmpeg                           # macOS; needed to read frames from a video
```
Requires **Python 3.10+** (tested on 3.13) and **ffmpeg** on your PATH.

### 1. Verify the install offline (no key)
```bash
python3 scripts/etu_understand.py --self-test    # universal engine: sample→extract→reconcile→route→lift
python3 scripts/etu_comprehend.py --self-test    # closed-set template classifier
```
Both must print `self-test: PASS`.

### 2. See the prebuilt scenes in the viewer (no key)
```bash
python3 scripts/etu_make.py --all     # build the 7 math sample scenes
python3 scripts/serve.py              # serves http://localhost:8000/viewer/
```
Open **http://localhost:8000/viewer/** (use the server, *not* `file://`). Pick a
scene from the **Scene** dropdown; drag to orbit, `Space` to play, slider to scrub.

### 3. Set your vision API key
```bash
export GEMINI_API_KEY=...          # the "eye" — extracts objects + changes from frames
export DEEPSEEK_API_KEY=sk-...     # optional "brain" — upgrades a clip to a correct math template when one fits
```
Vision alternatives: `OPENAI_API_KEY` (`--vision-provider openai`) or
`OPENROUTER_API_KEY` (`--vision-provider openrouter`). Gemini's default model is
`gemini-2.5-flash`.

### 4. Get a video — yours, or generate a test clip
Use your own 2D animation, **or** make one (no video needed):
```bash
python3 scripts/make_test_clip.py --out data/work/orbit.mp4   # a 2D orbit animation
```

### 5. Analyze the video → 3D scene
```bash
python3 scripts/etu_understand.py \
    --video data/work/orbit.mp4 \
    --vision-provider gemini \
    --mode general \
    --out data/samples/orbit_auto.json
```
What you'll see printed: how many keyframes were extracted, the one-line summary
the vision model produced, how many objects it found, and the saved scene path.
- `--mode general` always lifts generically (works on anything). `--mode auto`
  upgrades to a correct math template if the clip confidently matches one (needs
  `DEEPSEEK_API_KEY`); `--mode template` only templates.
- `--max-images N` (default 12) — how many change-selected frames the eye sees;
  raise it for fast/complex motion.
- No video, only images? Use `--frames path/to/pngs` instead of `--video`.

### 6. Validate and view the result
```bash
python3 scripts/mmi_validate.py data/samples/orbit_auto.json   # contract check (should be ✓)
```
With `scripts/serve.py` running, open the viewer, **hard-reload** (Cmd/Ctrl-Shift-R),
and either pick the scene from the dropdown or use **Load file…** / drag the
`.json` onto the window. You should see the objects move (and fade in/out) in 3D.

### Troubleshooting (issues actually seen during testing)
| Symptom | Fix |
| --- | --- |
| `self-test` import error | run from the `mmi-prototype/` dir, and `pip install -r requirements.txt` |
| `--video` errors "Neither OpenCV nor ffmpeg" | `brew install ffmpeg` (must be on PATH) |
| only 1–2 keyframes extracted, motion lost | already handled — the ETU path samples densely by change; if it persists, raise `--max-images` |
| Gemini `429 ... limit: 0` for a model | that model has no quota on your key; use default `gemini-2.5-flash` or `--vision-model gemini-flash-latest` |
| Gemini `400 Please pass a valid API key` | key invalid/rotated — paste a fresh one |
| `missing API key — set GEMINI_API_KEY` | `export` it in the *same* shell before running |
| Viewer all black / blank | you opened `file://` — use the `serve.py` localhost URL; and **hard-reload** to bust the cached `main.js` |
| Viewer "couldn't fetch sample" | run `scripts/serve.py`, or drag a `.json` in |
| Scene plays too fast to study | use the **Speed** control (0.25×) and scrub the slider |

### What to report back (honest soft spots — your feedback targets)
1. **Depth is approximate** — 2D→true-spatial depth is ambiguous; orbiting shows an
   *inferred* depth, while object **motion** and **time** are faithful.
2. **Vision extraction quality** — the eye is non-deterministic; with many/fast
   objects it can mislabel, miscount, or coarsen the timeline. Note the clip + what
   it got wrong.
3. **Keyframe spacing is uniform**, not yet proportional to real elapsed time
   between events.
4. **Surface shading** is flat (no per-frame lighting) — readability feedback welcome.

Note bugs as `file:line` or the command you ran + its output.

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
    router.py            # universal entry: extract → template-upgrade or general-lift
    templates/           # 7 math templates (complex_surface, fourier_stack, …)
    colormap.py
    comprehend/          # closed-set classify (catalog, llm, evidence, classify, vision)
    understand/          # universal engine:
      schema.py          #   FeatureGraph (domain-agnostic objects+features+changes)
      extract.py         #   frames → FeatureGraph (vision)
      sampling.py        #   change-driven frame selection
      identity.py        #   reconcile vision ID drift (split/duplicate)
      lift.py            #   FeatureGraph → 3D/4D Scene (event keyframes + lifetime)
  formats/mmi_scene.py   # mmi-lite schema (box/pointcloud/line/surface + morph + opacity)
  pipeline/, stages/     # legacy 3D-reconstruction path (for real multi-view capture)
viewer/                  # Three.js interactive viewer (interpolated pose + opacity)
scripts/                 # etu_understand, etu_make, etu_comprehend, mmi_validate,
                         # make_test_clip, serve, gen_sample, run_pipeline
docs/                    # ARCHITECTURE, ROADMAP, FILE_FORMAT, example_scene.json
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
