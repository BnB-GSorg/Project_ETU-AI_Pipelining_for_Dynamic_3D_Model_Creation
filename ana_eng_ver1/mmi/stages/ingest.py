"""Stage 1 — Ingest: decode an .mp4 and sample frames.

This stage is fully runnable on a Mac. It prefers OpenCV; if OpenCV is not
installed it shells out to ffmpeg. The output is a directory of numbered PNG
frames plus a small manifest.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mmi.pipeline.config import PipelineConfig


@dataclass
class IngestResult:
    frame_dir: Path
    frame_paths: list[Path]
    source_fps: float
    sampled_fps: float


def run(cfg: PipelineConfig) -> IngestResult:
    out = cfg.stage_dir("01_frames")
    try:
        return _ingest_opencv(cfg, out)
    except ImportError:
        if shutil.which("ffmpeg"):
            return _ingest_ffmpeg(cfg, out)
        raise RuntimeError(
            "Neither OpenCV nor ffmpeg is available. "
            "Install one: `pip install opencv-python` or `brew install ffmpeg`."
        )


def _ingest_opencv(cfg: PipelineConfig, out: Path) -> IngestResult:
    import cv2  # noqa: F401  (import here so the stage degrades gracefully)

    cap = cv2.VideoCapture(str(cfg.video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {cfg.video}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / cfg.target_fps))

    paths: list[Path] = []
    idx = kept = 0
    while kept < cfg.max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            p = out / f"frame_{kept:05d}.png"
            cv2.imwrite(str(p), frame)
            paths.append(p)
            kept += 1
        idx += 1
    cap.release()
    _write_manifest(out, paths, src_fps, src_fps / step)
    return IngestResult(out, paths, src_fps, src_fps / step)


def _ingest_ffmpeg(cfg: PipelineConfig, out: Path) -> IngestResult:
    pattern = str(out / "frame_%05d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(cfg.video), "-vf", f"fps={cfg.target_fps}",
         "-frames:v", str(cfg.max_frames), pattern],
        check=True, capture_output=True,
    )
    paths = sorted(out.glob("frame_*.png"))
    _write_manifest(out, paths, 0.0, cfg.target_fps)
    return IngestResult(out, paths, 0.0, cfg.target_fps)


def _write_manifest(out: Path, paths: list[Path], src_fps: float, sampled_fps: float) -> None:
    (out / "manifest.json").write_text(
        json.dumps(
            {"count": len(paths), "source_fps": src_fps, "sampled_fps": sampled_fps,
             "frames": [p.name for p in paths]},
            indent=2,
        )
    )
