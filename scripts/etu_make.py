#!/usr/bin/env python3
"""Author an ETU 3D scene from a template (template-first; no video yet).

Examples:
    python scripts/etu_make.py complex_surface --param func=z^3-1
    python scripts/etu_make.py graph_surface --param func=saddle --param n=48
    python scripts/etu_make.py fourier_stack --param harmonics=10
    python scripts/etu_make.py --all          # regenerate all sample scenes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.etu import LessonSpec, synthesize  # noqa: E402
from mmi.etu.templates import available  # noqa: E402

# default sample set written by --all (also feeds the viewer's scene picker)
SAMPLES = {
    "complex_surface": {"func": "z^3-1"},
    "graph_surface": {"func": "ripple"},
    "fourier_stack": {"harmonics": 9},
    "taylor_series": {"func": "sin", "terms": 6},
    "vector_field": {"field": "rotation", "density": 5},
    "linear_transform": {"matrix": "shear3d"},
    "parametric_surface": {"shape": "torus"},
}


def _coerce(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def make(concept: str, params: dict, out: Path) -> None:
    spec = LessonSpec(concept=concept, title="", params=params)
    scene = synthesize(spec)
    scene.save(out)
    print(f"  {concept:16s} -> {out}  ({out.stat().st_size/1024:.1f} KB, {scene.duration_frames} frames)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("concept", nargs="?", choices=available(), help="template id")
    ap.add_argument("--param", action="append", default=[], metavar="K=V", help="template parameter")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--all", action="store_true", help="regenerate every sample scene")
    args = ap.parse_args()

    outdir = Path("data/samples")
    if args.all:
        print("regenerating ETU sample scenes:")
        for concept, params in SAMPLES.items():
            make(concept, params, outdir / f"{concept}.json")
        return 0

    if not args.concept:
        ap.error("give a concept (or use --all). available: " + ", ".join(available()))
    params = dict(kv.split("=", 1) for kv in args.param)
    params = {k: _coerce(v) for k, v in params.items()}
    out = args.out or outdir / f"{args.concept}.json"
    make(args.concept, params, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
