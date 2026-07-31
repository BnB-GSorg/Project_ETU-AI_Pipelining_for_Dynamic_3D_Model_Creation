"""Stage 2 — Keyframe selection ("关键帧").

Pick the frames worth reconstructing from. "content" mode keeps a frame when it
differs enough from the last kept frame (scene/process change); "uniform" keeps
every Nth. Runs on a Mac with numpy + Pillow/OpenCV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mmi.pipeline.config import PipelineConfig
from mmi.stages.ingest import IngestResult


@dataclass
class KeyframeResult:
    keyframe_paths: list[Path]
    indices: list[int]


def run(cfg: PipelineConfig, ingest: IngestResult) -> KeyframeResult:
    """Select keyframes from the primary view (view 0).

    In single-view mode, processes view_0. In multi-view mode, keyframe selection
    is done on view 0 (reference) and the same frame indices are used for all views.
    """
    # Use view 0 as the reference for content-based keyframe selection
    primary = ingest.views[0]
    if cfg.keyframe_method == "uniform":
        idxs = list(range(0, len(primary.frame_paths), max(1, len(primary.frame_paths) // 24 or 1)))
        return KeyframeResult([primary.frame_paths[i] for i in idxs], idxs)
    return _content_select(cfg, primary)


def _load_gray(path: Path) -> np.ndarray:
    try:
        import cv2

        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        return img.astype(np.float32)
    except ImportError:
        from PIL import Image

        return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def _content_select(cfg: PipelineConfig, primary: "ViewFrames") -> KeyframeResult:
    from mmi.stages.ingest import ViewFrames  # avoid circular import
    kept_idx: list[int] = []
    kept_paths: list[Path] = []
    prev: np.ndarray | None = None
    for i, p in enumerate(primary.frame_paths):
        g = _load_gray(p)
        if prev is None or float(np.mean(np.abs(g - prev))) >= cfg.keyframe_threshold:
            kept_idx.append(i)
            kept_paths.append(p)
            prev = g
    # always keep the final frame so the end-state is reconstructable
    if primary.frame_paths and kept_idx[-1] != len(primary.frame_paths) - 1:
        kept_idx.append(len(primary.frame_paths) - 1)
        kept_paths.append(primary.frame_paths[-1])
    return KeyframeResult(kept_paths, kept_idx)
