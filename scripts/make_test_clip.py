#!/usr/bin/env python3
"""Render a simple 2D explainer-style animation to an .mp4 for end-to-end testing.

Produces a flat 2D "orbit" animation (the kind of thing ETU is meant to lift to
3D): a yellow sun at the center, a blue planet and an orange planet orbiting it
at different radii/speeds, plus a small grey comet that appears partway through
and leaves the frame (to exercise object lifetime). No domain labels — it is just
moving colored discs, which is exactly what the general engine should handle.

    python scripts/make_test_clip.py --out data/work/orbit.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def render(out: Path, n_frames: int = 72, fps: int = 24) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="orbit_"))
    for i in range(n_frames):
        t = i / n_frames
        fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=100)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-0.75, 0.75)
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)

        # sun (static center)
        ax.add_patch(plt.Circle((0, 0), 0.12, color="#f4b400", zorder=3))
        # blue planet — inner, fast
        a1 = 2 * np.pi * t * 2.0
        ax.add_patch(plt.Circle((0.42 * np.cos(a1), 0.42 * np.sin(a1)), 0.06, color="#1a73e8", zorder=3))
        # orange planet — outer, slow
        a2 = 2 * np.pi * t * 1.0 + 1.0
        ax.add_patch(plt.Circle((0.72 * np.cos(a2), 0.72 * np.sin(a2)), 0.05, color="#e8711a", zorder=3))
        # grey comet — appears for the middle third, crossing left->right
        if 0.33 <= t <= 0.66:
            cx = -1.0 + (t - 0.33) / 0.33 * 2.0
            ax.add_patch(plt.Circle((cx, 0.5), 0.035, color="#888888", zorder=3))

        ax.set_aspect("equal")
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        fig.savefig(tmp / f"f{i:03d}.png")
        plt.close(fig)

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp / "f%03d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
        check=True, capture_output=True,
    )
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/work/orbit.mp4"))
    ap.add_argument("--frames", type=int, default=72)
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args()
    p = render(a.out, a.frames, a.fps)
    print(f"wrote {p}  ({p.stat().st_size/1024:.0f} KB)")
