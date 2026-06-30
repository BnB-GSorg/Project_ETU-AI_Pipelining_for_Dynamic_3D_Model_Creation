"""Pipeline configuration — one dataclass threaded through every stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    video: Path                       # input .mp4
    workdir: Path                     # scratch + artifacts root
    out_scene: Path                   # final mmi-lite .json

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

    def stage_dir(self, name: str) -> Path:
        d = self.workdir / name
        d.mkdir(parents=True, exist_ok=True)
        return d
