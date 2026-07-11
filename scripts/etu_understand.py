#!/usr/bin/env python3
"""ETU universal — any 2D animation -> 3D/4D scene (general engine + template upgrade).

    video/frames --[vision]--> FeatureGraph --+--(template upgrade if it fits)--> Scene
                                              +--(general lift otherwise)-------> Scene

Examples:
    # general engine on any animation (extract objects+changes, lift to 3D)
    python scripts/etu_understand.py --video reaction.mp4 --vision-provider gemini --out data/samples/auto.json

    # auto: upgrade to a correct template when the content matches, else general
    python scripts/etu_understand.py --video clip.mp4 --vision-provider gemini --mode auto

    # offline self-test (no keys / network)
    python scripts/etu_understand.py --self-test

Keys (env): vision eye -> GEMINI_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY;
template upgrade brain -> DEEPSEEK_API_KEY.
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
    # Return a DENSE, evenly-timed pool; extract() then samples it by *change*
    # (dense where the animation moves, sparse where it's still). We skip the
    # reconstruction keyframer here — its content-dedup throws away the very
    # resolution the change-sampler needs.
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

    # b) ROUTER template-upgrade: vision summary matches a known template
    fake_eye = lambda s, u, imgs: json.dumps({
        "summary": "A square wave is built by adding sine harmonics until it converges",
        "fps": 12, "duration": 3,
        "objects": [{"id": "w", "label": "waveform", "shape": "tube", "color": "#fff",
                     "timeline": [{"t": 0, "x": 0.5, "y": 0.5, "size": 0.4}]}]})
    fake_brain = lambda s, u: json.dumps(
        {"concept": "fourier_stack", "params": {"harmonics": 8}, "confidence": 0.9, "rationale": "square wave from harmonics"})
    r = comprehend_any(frames=[Path("f.png")], chat_eye=fake_eye, chat_brain=fake_brain, prefer="auto")
    print(f"  [router ] method={r.method} concept={r.concept} valid={not r.scene.validate()}")
    ok = ok and r.method == "template" and not r.scene.validate()

    # c) ROUTER general fallback: vision summary matches nothing known
    fake_eye2 = lambda s, u, imgs: json.dumps({
        "summary": "A cell divides into two", "fps": 10, "duration": 3,
        "objects": [{"id": "c", "label": "cell", "shape": "sphere", "color": "#7CFC00",
                     "timeline": [{"t": 0, "x": 0.5, "y": 0.5, "size": 0.3}, {"t": 2, "x": 0.4, "y": 0.5, "size": 0.2}]}]})
    fake_brain2 = lambda s, u: json.dumps({"concept": "none", "confidence": 0.1, "rationale": "no template"})
    r2 = comprehend_any(frames=[Path("f.png")], chat_eye=fake_eye2, chat_brain=fake_brain2, prefer="auto")
    print(f"  [router ] method={r2.method} (fallback) valid={not r2.scene.validate()}")
    ok = ok and r2.method == "general" and not r2.scene.validate()

    # d) IDENTITY reconcile: a vision model split one ball into two ids across time
    from mmi.etu.understand.identity import reconcile
    split = FeatureGraph.from_dict({
        "summary": "one blue ball crosses the screen", "fps": 12, "duration": 4,
        "objects": [
            {"id": "b1", "label": "blue ball", "shape": "sphere", "color": "#1a73e8",
             "timeline": [{"t": 0, "x": 0.1, "y": 0.5}, {"t": 1, "x": 0.35, "y": 0.5}]},
            {"id": "b2", "label": "blue ball", "shape": "sphere", "color": "#1b74e9",  # ~same color, later
             "timeline": [{"t": 2, "x": 0.6, "y": 0.5}, {"t": 3, "x": 0.85, "y": 0.5}]},
            {"id": "r", "label": "red ball", "shape": "sphere", "color": "#ef4444",
             "timeline": [{"t": 0, "x": 0.5, "y": 0.2}, {"t": 3, "x": 0.5, "y": 0.2}]},
        ]})
    reconcile(split)
    blue = [o for o in split.objects if _color_dist_ok(o.color, "#1a73e8")]
    merged_ok = len(split.objects) == 2 and len(blue) == 1 and len(blue[0].timeline) == 4
    print(f"  [identity] split blue ball stitched -> {len(split.objects)} objects "
          f"(blue has {len(blue[0].timeline) if blue else 0}/4 states), ok={merged_ok}")
    ok = ok and merged_ok

    # e) CHANGE-DRIVEN sampling: a still clip with one burst of motion in the middle
    import numpy as np

    from mmi.etu.understand.sampling import pick_indices
    sig = np.zeros(40, dtype=np.float32)
    sig[18:23] = 5.0                      # all the change happens in frames 18..22
    picks = pick_indices(sig, 8)
    in_burst = sum(1 for i in picks if 17 <= i <= 23)
    uniform_in_burst = sum(1 for i in (round(j * 39 / 7) for j in range(8)) if 17 <= i <= 23)
    sampling_ok = picks[0] == 0 and picks[-1] == 39 and in_burst > uniform_in_burst
    print(f"  [sampling] burst@18-22: change-driven puts {in_burst} samples in the burst "
          f"vs {uniform_in_burst} for uniform, ok={sampling_ok}")
    ok = ok and sampling_ok

    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _color_dist_ok(a: str, b: str) -> bool:
    from mmi.etu.understand.identity import _color_dist, COLOR_TOL
    return _color_dist(a, b) <= COLOR_TOL


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path)
    ap.add_argument("--frames", type=Path)
    ap.add_argument("--transcript", type=Path)
    ap.add_argument("--hint", default="")
    ap.add_argument("--mode", default="auto", choices=["auto", "template", "general"])
    ap.add_argument("--vision-provider", default="gemini")
    ap.add_argument("--vision-model", default=None)
    ap.add_argument("--provider", default="deepseek", help="template-upgrade brain")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-images", type=int, default=12,
                    help="how many evenly-spaced frames the vision model sees (more = finer motion)")
    ap.add_argument("--min-confidence", type=float, default=0.55)
    ap.add_argument("--workdir", type=Path, default=Path("data/work"))
    ap.add_argument("--out", type=Path, default=Path("data/samples/auto.json"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    frames: list[Path] = []
    if args.video:
        print(f"extracting keyframes from {args.video} ...")
        frames = _extract_frames(args.video, args.workdir)
        print(f"  -> {len(frames)} keyframes")
    elif args.frames:
        frames = sorted(args.frames.glob("*.png"))
    if not frames:
        ap.error("provide --video or --frames (the general engine needs frames)")

    transcript_text = gather(transcript=args.transcript, hint=args.hint).transcript if args.transcript else ""
    vcfg = make_config(args.vision_provider, args.vision_model)
    bcfg = make_config(args.provider, args.model)
    print(f"vision eye: {vcfg.provider}:{vcfg.model}  |  brain: {bcfg.provider}:{bcfg.model}  |  mode={args.mode}")

    r = comprehend_any(frames=frames, transcript_text=transcript_text, hint=args.hint,
                       brain_cfg=bcfg, vision_cfg=vcfg, prefer=args.mode, min_confidence=args.min_confidence)

    if r.feature_graph:
        print(f"  extracted: {len(r.feature_graph.objects)} objects — \"{r.feature_graph.summary[:70]}\"")
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
