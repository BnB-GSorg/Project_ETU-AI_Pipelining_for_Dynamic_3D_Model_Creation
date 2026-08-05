#!/usr/bin/env python3
"""ETU universal — any 2D animation -> 3D/4D scene (single reasoning model + CV tools).

    frames --[CV analysis]--> FeatureGraph --+--(template upgrade if it fits)--> Scene
                                             +--(general lift otherwise)-------> Scene

Architecture: ONE reasoning model (DeepSeek) with CV/3D modules as tools.
No separate vision LLM — deterministic CV (optical flow, edge detection,
contour finding, color segmentation) extracts raw visual features from
frames. The reasoning model interprets them, labels objects, and decides
template vs general lift.

Examples:
    # general engine on any animation (CV extracts objects, brain decides)
    python scripts/etu_understand.py --video reaction.mp4 --out data/samples/auto.json

    # auto: upgrade to a correct template when the content matches, else general
    python scripts/etu_understand.py --video clip.mp4 --mode auto

    # offline self-test (no keys / network — CV only)
    python scripts/etu_understand.py --self-test

Keys (env): reasoning model -> DEEPSEEK_API_KEY (for template upgrade path).
CV analysis runs locally with no API keys needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.etu.comprehend import gather  # noqa: E402
from mmi.etu.comprehend.llm import make_config  # noqa: E402
from mmi.etu.router import comprehend_any  # noqa: E402
from mmi.etu.understand import lift  # noqa: E402
from mmi.etu.understand.schema import FeatureGraph  # noqa: E402


def _extract_frames(video: Path, workdir: Path, target_fps: float = 10.0) -> list[Path]:
    from mmi.pipeline.config import PipelineConfig
    from mmi.stages import ingest
    cfg = PipelineConfig(video=video, workdir=workdir, out_scene=workdir / "_unused.json",
                         target_fps=target_fps, max_frames=240)
    return ingest.run(cfg).frame_paths


def _self_test() -> int:
    ok = True

    # a) GENERAL lift: a generic animation the engine has no template for
    fg = FeatureGraph.from_dict({
        "summary": "Two particles approach and collide, then rebound",
        "fps": 12, "duration": 4,
        "objects": [
            {"id": "a", "label": "blue ball", "shape": "sphere", "color": "#3b82f6", "depth": 0.4,
             "timeline": [{"t": 0, "x": 0.1, "y": 0.5, "size": 0.1}, {"t": 1, "x": 0.4, "y": 0.5, "size": 0.1},
                          {"t": 2, "x": 0.45, "y": 0.5, "size": 0.12}, {"t": 3, "x": 0.2, "y": 0.5, "size": 0.1}]},
            {"id": "b", "label": "red ball", "shape": "sphere", "color": "#ef4444", "depth": 0.6,
             "timeline": [{"t": 0, "x": 0.9, "y": 0.5, "size": 0.1}, {"t": 1, "x": 0.6, "y": 0.5, "size": 0.1},
                          {"t": 2, "x": 0.55, "y": 0.5, "size": 0.12}, {"t": 3, "x": 0.8, "y": 0.5, "size": 0.1}]},
        ]})
    scene = lift(fg)
    valid = not scene.validate()
    print(f"  [general] lifted {len(fg.objects)} objects -> {len(scene.objects)} scene objs, valid={valid}")
    ok = ok and valid

    # b) ROUTER template-upgrade: reasoning model matches a known template
    fake_brain = lambda s, u: json.dumps(
        {"concept": "fourier_stack", "params": {"harmonics": 8}, "confidence": 0.9,
         "rationale": "square wave from harmonics"})
    # Feed pre-built evidence (no frames needed — tests reasoning model only)
    r2 = comprehend_any(frames=None, transcript_text="A square wave is built by adding sine harmonics",
                        chat_brain=fake_brain, prefer="auto")
    print(f"  [router ] method={r2.method} concept={r2.concept} valid={not r2.scene.validate() if r2.scene else 'N/A'}")
    ok = ok and r2.method == "template" and not r2.scene.validate()

    # c) ROUTER general fallback: reasoning model matches nothing known
    fake_brain2 = lambda s, u: json.dumps({"concept": "none", "confidence": 0.1, "rationale": "no template"})
    r3 = comprehend_any(frames=None, transcript_text="A cell divides into two",
                        chat_brain=fake_brain2, prefer="auto")
    print(f"  [router ] method={r3.method} (no match) concept={r3.concept}")

    # d) CV VISION MODULE self-test
    try:
        from mmi.etu.vision import analyze, feature_graph_from_analysis
        import numpy as np
        # Create synthetic test frames using numpy
        from PIL import Image
        import tempfile, os
        
        tmpdir = tempfile.mkdtemp()
        frames = []
        for i in range(5):
            # Create a simple frame with a moving blob
            img = np.zeros((64, 64, 3), dtype=np.uint8)
            x = 10 + i * 8  # blob moves right
            img[25:40, x:x+15] = [59, 130, 246]  # blue blob
            path = Path(tmpdir) / f"frame_{i:03d}.png"
            Image.fromarray(img).save(path)
            frames.append(path)
        
        analysis = analyze(frames, size=64)
        fg_cv = feature_graph_from_analysis(analysis, fps=12)
        cv_ok = len(fg_cv.objects) >= 1
        print(f"  [cv     ] CV analysis: {analysis.n_frames} frames, {len(fg_cv.objects)} objects detected, ok={cv_ok}")
        ok = ok and cv_ok
        
        import shutil
        shutil.rmtree(tmpdir)
    except ImportError as e:
        print(f"  [cv     ] SKIP (missing dep: {e})")
    except Exception as e:
        print(f"  [cv     ] FAIL: {e}")
        ok = False

    # e) IDENTITY reconcile
    from mmi.etu.understand.identity import reconcile
    split = FeatureGraph.from_dict({
        "summary": "one blue ball crosses the screen", "fps": 12, "duration": 4,
        "objects": [
            {"id": "b1", "label": "blue ball", "shape": "sphere", "color": "#1a73e8",
             "timeline": [{"t": 0, "x": 0.1, "y": 0.5}, {"t": 1, "x": 0.35, "y": 0.5}]},
            {"id": "b2", "label": "blue ball", "shape": "sphere", "color": "#1b74e9",
             "timeline": [{"t": 2, "x": 0.6, "y": 0.5}, {"t": 3, "x": 0.85, "y": 0.5}]},
            {"id": "r", "label": "red ball", "shape": "sphere", "color": "#ef4444",
             "timeline": [{"t": 0, "x": 0.5, "y": 0.2}, {"t": 3, "x": 0.5, "y": 0.2}]},
        ]})
    reconcile(split)
    from mmi.etu.understand.identity import _color_dist, COLOR_TOL
    blue = [o for o in split.objects if _color_dist(o.color, "#1a73e8") <= COLOR_TOL]
    merged_ok = len(split.objects) == 2 and len(blue) == 1 and len(blue[0].timeline) == 4
    print(f"  [identity] split blue ball stitched -> {len(split.objects)} objects "
          f"(blue has {len(blue[0].timeline) if blue else 0}/4 states), ok={merged_ok}")
    ok = ok and merged_ok

    # f) CHANGE-DRIVEN sampling
    import numpy as np
    from mmi.etu.understand.sampling import pick_indices
    sig = np.zeros(40, dtype=np.float32)
    sig[18:23] = 5.0
    picks = pick_indices(sig, 8)
    in_burst = sum(1 for i in picks if 17 <= i <= 23)
    uniform_in_burst = sum(1 for i in (round(j * 39 / 7) for j in range(8)) if 17 <= i <= 23)
    sampling_ok = picks[0] == 0 and picks[-1] == 39 and in_burst > uniform_in_burst
    print(f"  [sampling] burst@18-22: change-driven puts {in_burst} samples in the burst "
          f"vs {uniform_in_burst} for uniform, ok={sampling_ok}")
    ok = ok and sampling_ok

    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path)
    ap.add_argument("--frames", type=Path)
    ap.add_argument("--transcript", type=Path)
    ap.add_argument("--hint", default="")
    ap.add_argument("--mode", default="auto", choices=["auto", "template", "general"])
    ap.add_argument("--provider", default="deepseek", help="reasoning model provider (the sole LLM)")
    ap.add_argument("--model", default=None, help="reasoning model name")
    ap.add_argument("--max-cv-images", type=int, default=8,
                    help="max frames for CV analysis (change-driven sampling)")
    ap.add_argument("--min-confidence", type=float, default=0.55)
    ap.add_argument("--workdir", type=Path, default=Path("data/work"))
    ap.add_argument("--out", type=Path, default=Path("data/samples/auto.json"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    frames: list[Path] = []
    if args.video:
        print(f"extracting frames from {args.video} ...")
        frames = _extract_frames(args.video, args.workdir)
        print(f"  -> {len(frames)} frames")
    elif args.frames:
        frames = sorted(args.frames.glob("*.png"))
    if not frames:
        ap.error("provide --video or --frames (CV analysis needs frames)")

    transcript_text = gather(transcript=args.transcript, hint=args.hint).transcript if args.transcript else ""
    bcfg = make_config(args.provider, args.model)
    print(f"reasoning model: {bcfg.provider}:{bcfg.model}  |  mode={args.mode}")
    print(f"CV analysis: deterministic (optical flow + contours + colors), max {args.max_cv_images} frames")

    r = comprehend_any(frames=frames, transcript_text=transcript_text, hint=args.hint,
                       brain_cfg=bcfg, prefer=args.mode, min_confidence=args.min_confidence,
                       max_cv_images=args.max_cv_images)

    if r.feature_graph:
        n_objs = len(r.feature_graph.objects)
        objs_str = ", ".join(f"{o.id}({o.shape})" for o in r.feature_graph.objects[:5])
        print(f"  CV extracted: {n_objs} objects — [{objs_str}]")
    print(f"  method    : {r.method}  ({r.concept}, confidence {r.confidence:.2f})")
    if not r.scene:
        print(f"FAILED — {r.rationale}")
        return 2
    r.scene.save(args.out)
    print(f"authored -> {args.out}  ({args.out.stat().st_size/1024:.1f} KB, {r.scene.duration_frames} frames)")
    print("open the viewer and drag this file in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
