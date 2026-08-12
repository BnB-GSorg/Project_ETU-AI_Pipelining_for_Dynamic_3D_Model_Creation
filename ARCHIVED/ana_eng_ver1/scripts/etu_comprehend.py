#!/usr/bin/env python3
"""ETU E3 — comprehend a 2D explainer and author the 3D scene (hybrid).

Hybrid comprehension:
    video -> keyframes --(vision "eye")--> visual description --+
    transcript / OCR / hint -----------------------------------+--> DeepSeek
                                                                     closed-set "brain"
                                                                  -> LessonSpec -> 3D scene

The vision eye only DESCRIBES frames; DeepSeek makes the closed-set decision.
Run text-only (no vision key) or hybrid (add --vision-provider).

Examples:
    # text-only (DeepSeek brain on a transcript)
    python scripts/etu_comprehend.py --transcript lecture.vtt --out data/samples/auto.json

    # hybrid: extract frames from the mp4, describe them with a vision model, then classify
    python scripts/etu_comprehend.py --video clip.mp4 --vision-provider gemini \\
        --transcript lecture.vtt --out data/samples/auto.json

    # offline self-test (no keys / network)
    python scripts/etu_comprehend.py --self-test

Keys (env): DEEPSEEK_API_KEY (brain). Vision eye: GEMINI_API_KEY / OPENAI_API_KEY /
OPENROUTER_API_KEY depending on --vision-provider.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.etu import LessonSpec, synthesize  # noqa: E402
from mmi.etu.comprehend import comprehend, describe_frames, gather  # noqa: E402
from mmi.etu.comprehend.evidence import Evidence  # noqa: E402
from mmi.etu.comprehend.llm import make_config  # noqa: E402


def _extract_frames(video: Path, workdir: Path) -> list[Path]:
    """Reuse the ingest + keyframe stages to get keyframes from an mp4."""
    from mmi.pipeline.config import PipelineConfig
    from mmi.stages import ingest, keyframes

    cfg = PipelineConfig(video=video, workdir=workdir, out_scene=workdir / "_unused.json")
    ing = ingest.run(cfg)
    kf = keyframes.run(cfg, ing)
    return kf.keyframe_paths


def _self_test() -> int:
    """Exercise the whole hybrid path offline with fake eye + brain."""
    ok = True

    # 1) vision "eye" assembly works without network (fake chat_fn ignores images)
    fake_eye = lambda s, u, imgs: "A green 3D surface plotted over an x-y grid; it starts flat then rises into a saddle shape."
    desc = describe_frames([Path("f1.png"), Path("f2.png")], chat_fn=fake_eye)
    print(f"  [eye] description: {desc[:60]}...")

    # 2) brain classifies combined evidence (vision + transcript), and abstains off-topic
    cases = {
        "fourier": ("We add sine harmonics to build a square wave; the partial sums converge.",
                    {"concept": "fourier_stack", "params": {"harmonics": 9}, "confidence": 0.92, "rationale": "square wave from harmonics"}),
        "complex": ("Domain coloring of f(z)=z^3-1 with its roots.",
                    {"concept": "complex_surface", "params": {"func": "z^3-1"}, "confidence": 0.88, "rationale": "complex domain coloring"}),
        "hybrid":  ("(sparse narration)",  # relies on the vision description
                    {"concept": "graph_surface", "params": {"func": "saddle"}, "confidence": 0.8, "rationale": "saddle surface seen in frames"}),
        "offtopic": ("A documentary about Roman emperors.",
                    {"concept": "none", "params": {}, "confidence": 0.1, "rationale": "unrelated"}),
    }
    for key, (transcript, fake) in cases.items():
        ev = Evidence(transcript=transcript, vision=desc if key == "hybrid" else "")
        c = comprehend(ev.as_text(), chat_fn=lambda s, u, _f=fake: json.dumps(_f))
        if c.spec:
            valid = not synthesize(c.spec).validate()
            print(f"  [{key:8s}] -> {c.concept:16s} conf={c.confidence:.2f} valid={valid}")
            ok = ok and valid
        else:
            print(f"  [{key:8s}] -> ABSTAIN ({c.rationale})")
            ok = ok and (key == "offtopic")
    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, help="mp4 to extract keyframes from (for vision/OCR)")
    ap.add_argument("--frames", type=Path, help="existing dir of keyframe PNGs")
    ap.add_argument("--transcript", type=Path, help=".srt/.vtt/.txt narration")
    ap.add_argument("--hint", default="", help="manual hint text")
    ap.add_argument("--ocr", action="store_true", help="OCR the frames (needs pytesseract)")
    ap.add_argument("--vision-provider", default=None, help="enable hybrid eye: gemini|openai|openrouter")
    ap.add_argument("--vision-model", default=None)
    ap.add_argument("--max-images", type=int, default=6)
    ap.add_argument("--provider", default="deepseek", help="text brain provider")
    ap.add_argument("--model", default=None)
    ap.add_argument("--min-confidence", type=float, default=0.45)
    ap.add_argument("--workdir", type=Path, default=Path("data/work"))
    ap.add_argument("--out", type=Path, default=Path("data/samples/auto.json"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    # resolve frames
    frames: list[Path] = []
    frames_dir: Path | None = None
    if args.video:
        print(f"extracting keyframes from {args.video} ...")
        frames = _extract_frames(args.video, args.workdir)
        frames_dir = frames[0].parent if frames else None
        print(f"  -> {len(frames)} keyframes")
    elif args.frames:
        frames_dir = args.frames
        frames = sorted(args.frames.glob("*.png"))

    # text evidence (transcript + optional OCR + hint)
    ev = gather(transcript=args.transcript, frames_dir=(frames_dir if args.ocr else None), hint=args.hint)

    # vision "eye" (hybrid)
    if args.vision_provider:
        if not frames:
            ap.error("--vision-provider needs frames: pass --video or --frames")
        vcfg = make_config(args.vision_provider, args.vision_model)
        print(f"vision eye: describing {min(len(frames), args.max_images)} frames with {vcfg.provider}:{vcfg.model} ...")
        ev.vision = describe_frames(frames, cfg=vcfg, hint=args.hint, max_images=args.max_images)
        print(f"  -> {len(ev.vision)} chars of visual description")

    if ev.as_text() == "(no evidence provided)":
        ap.error("no evidence — provide --transcript, --hint, or --vision-provider with frames")

    # text "brain": closed-set classification
    bcfg = make_config(args.provider, args.model)
    print(f"brain: classifying with {bcfg.provider}:{bcfg.model} ...")
    c = comprehend(ev.as_text(), cfg=bcfg, min_confidence=args.min_confidence,
                   source_video=str(args.video or args.transcript or args.frames or ""))

    print(f"  concept   : {c.concept}")
    print(f"  confidence: {c.confidence:.2f}")
    print(f"  rationale : {c.rationale}")
    if not c.spec:
        print("ABSTAINED — no confident template match. Nothing authored.")
        return 2

    print(f"  params    : {c.spec.params}")
    scene = synthesize(c.spec)
    scene.save(args.out)
    print(f"authored -> {args.out}  ({args.out.stat().st_size/1024:.1f} KB, {scene.duration_frames} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
