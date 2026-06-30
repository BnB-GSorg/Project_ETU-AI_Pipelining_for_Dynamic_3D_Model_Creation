#!/usr/bin/env python3
"""Run the full video -> mmi-lite pipeline.

Example:
    python scripts/run_pipeline.py input.mp4 --backend synthetic --out data/samples/recon.json

Backends: synthetic (no deps, runs anywhere) | colmap | 3dgs | dyn-nerf (GPU).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.pipeline.config import PipelineConfig  # noqa: E402
from mmi.pipeline.pipeline import run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", type=Path)
    ap.add_argument("--workdir", type=Path, default=Path("data/work"))
    ap.add_argument("--out", type=Path, default=Path("data/samples/recon.json"))
    ap.add_argument("--backend", default="synthetic", choices=["synthetic", "colmap", "3dgs", "dyn-nerf"])
    ap.add_argument("--target-fps", type=float, default=4.0)
    ap.add_argument("--segmenter", default="color", choices=["color", "sam"])
    ap.add_argument("--track", default="flow", choices=["flow", "deform"])
    args = ap.parse_args()

    cfg = PipelineConfig(
        video=args.video,
        workdir=args.workdir,
        out_scene=args.out,
        recon_backend=args.backend,
        target_fps=args.target_fps,
        segmenter=args.segmenter,
        track_method=args.track,
    )
    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
