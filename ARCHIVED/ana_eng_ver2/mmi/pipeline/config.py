"""Pipeline configuration — one dataclass threaded through every stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    """All configuration needed by the pipeline stages — IO paths, backend selection, and tuning params."""

    workdir: Path                     # scratch + artifacts root
    out_scene: Path                   # final mmi-lite .json

    # --- input videos (single-view or multi-view) ---
    video: Path | None = None       # single-view (backward compat)
    videos: list[Path] | None = None  # multi-view: [cam0.mp4, cam1.mp4, cam2.mp4]

    # --- ingest / keyframes ---
    target_fps: float = 4.0           # frames/sec to sample from the video
    max_frames: int = 240             # hard cap on extracted frames
    keyframe_method: str = "content"  # "content" (scene change) | "uniform"
    keyframe_threshold: float = 12.0  # mean abs diff threshold for "content"

    # --- reconstruction backend (GPU stages) ---
    # "colmap"  : classic SfM/MVS (CPU-feasible, slow)
    # "3dgs"    : static Gaussian splatting per time-window
    # "dyn-nerf": dynamic NeRF / 4D Gaussian splatting (needs CUDA)
    recon_backend: str = "colmap"
    num_objects: int = 1              # brief: "Begin with one obj only first"

    # --- segmentation / tracking ---
    segmenter: str = "color"          # "color" (HSV clusters) | "sam" (GPU)
    track_method: str = "flow"        # "flow" (optical flow) | "deform" (learned field)

    extra: dict = field(default_factory=dict)

    def get_videos(self) -> list[Path]:
        if self.videos:
            return [Path(v) for v in self.videos]
        if self.video:
            return [Path(self.video)]
        raise ValueError("No video(s) configured — set video= or videos=")

    def is_multi_view(self) -> bool:
        return self.videos is not None and len(self.videos) > 1

    def stage_dir(self, name: str) -> Path:
        d = self.workdir / name
        d.mkdir(parents=True, exist_ok=True)
        return d
