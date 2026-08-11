"""Stage 1 — Ingest: decode .mp4(s) and sample frames.

Multi-view support: when multiple synchronized videos are provided
(cam0.mp4, cam1.mp4, cam2.mp4), each is processed independently into its
own subdirectory. All views are verified to have matching frame counts.

Backends: prefers OpenCV; falls back to ffmpeg.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mmi.pipeline.config import PipelineConfig


@dataclass
class ViewFrames:
    """Frames extracted from one camera view."""

    frame_dir: Path
    frame_paths: list[Path]
    source_fps: float
    sampled_fps: float


@dataclass
class IngestResult:
    """Output of multi-view ingest — one ViewFrames per camera."""

    views: dict[int, ViewFrames]  # camera_index → frames

    @property
    def is_multi_view(self) -> bool:
        return len(self.views) > 1

    @property
    def frame_count(self) -> int:
        return len(next(iter(self.views.values())).frame_paths)

    @property
    def view_count(self) -> int:
        return len(self.views)


def run(cfg: PipelineConfig) -> IngestResult:
    """Ingest one or more videos into frame directories.

    Single-view: backward-compatible, one view at index 0.
    Multi-view:  each camera gets view_00/, view_01/, etc.
    Verifies all views produce the same frame count.
    """
    videos = cfg.get_videos()
    views: dict[int, ViewFrames] = {}

    for i, video in enumerate(videos):
        out = cfg.stage_dir(f"01_frames/view_{i:02d}")
        result = _ingest_one(video, out, cfg)
        views[i] = result

    # ── Synchronization check ──
    if len(views) > 1:
        counts = {i: len(v.frame_paths) for i, v in views.items()}
        if len(set(counts.values())) > 1:
            raise ValueError(
                f"Multi-view videos have different frame counts: {counts}. "
                "All views must be synchronized (same length, same fps)."
            )
        expected_fps = next(iter(views.values())).sampled_fps
        for i, v in views.items():
            if abs(v.sampled_fps - expected_fps) > 0.1:
                raise ValueError(
                    f"View {i} sampled fps {v.sampled_fps:.1f} != view 0 "
                    f"fps {expected_fps:.1f}. All views must have the same framerate."
                )

    return IngestResult(views)


def _ingest_one(video: Path, out: Path, cfg: PipelineConfig) -> ViewFrames:
    out.mkdir(parents=True, exist_ok=True)
    try:
        return _ingest_opencv(video, out, cfg)
    except ImportError:
        if shutil.which("ffmpeg"):
            return _ingest_ffmpeg(video, out, cfg)
        raise RuntimeError(
            "Neither OpenCV nor ffmpeg is available. "
            "Install one: `pip install opencv-python` or `brew install ffmpeg`."
        )


def _ingest_opencv(video: Path, out: Path, cfg: PipelineConfig) -> ViewFrames:
    """Extract frames using OpenCV VideoCapture — skip-frames based on target fps."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")
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
    return ViewFrames(out, paths, src_fps, src_fps / step)


def _ingest_ffmpeg(video: Path, out: Path, cfg: PipelineConfig) -> ViewFrames:
    pattern = str(out / "frame_%05d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vf", f"fps={cfg.target_fps}",
         "-frames:v", str(cfg.max_frames), pattern],
        check=True, capture_output=True,
    )
    paths = sorted(out.glob("frame_*.png"))
    _write_manifest(out, paths, 0.0, cfg.target_fps)
    return ViewFrames(out, paths, 0.0, cfg.target_fps)


def _write_manifest(out: Path, paths: list[Path], src_fps: float, sampled_fps: float) -> None:
    (out / "manifest.json").write_text(
        json.dumps(
            {"count": len(paths), "source_fps": src_fps, "sampled_fps": sampled_fps,
             "frames": [p.name for p in paths]},
            indent=2,
        )
    )
