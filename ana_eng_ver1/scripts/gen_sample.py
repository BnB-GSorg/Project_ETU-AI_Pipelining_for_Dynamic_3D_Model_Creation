#!/usr/bin/env python3
"""Generate the synthetic Rubik's-cube sample scene for the viewer demo.

Usage:
    python scripts/gen_sample.py [--out data/samples/rubiks.json] [--moves "R U R' U'"]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow running as a plain script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.synth.rubiks import build_scene  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/samples/rubiks.json", type=Path)
    ap.add_argument("--moves", default=None, help="space-separated move list, e.g. \"R U R' U'\"")
    ap.add_argument("--frames-per-move", type=int, default=9)
    args = ap.parse_args()

    moves = args.moves.split() if args.moves else None
    scene = build_scene(moves=moves, frames_per_move=args.frames_per_move)

    problems = scene.validate()
    if problems:
        print("Scene validation FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    out = scene.save(args.out)
    size_kb = out.stat().st_size / 1024
    print(
        f"Wrote {out} ({size_kb:.1f} KB): "
        f"{len(scene.objects)} objects, {scene.duration_frames} frames, "
        f"{len(scene.events)} moves."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
