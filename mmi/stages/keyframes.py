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
    if cfg.keyframe_method == "uniform":
        idxs = list(range(0, len(ingest.frame_paths), max(1, len(ingest.frame_paths) // 24 or 1)))
        return KeyframeResult([ingest.frame_paths[i] for i in idxs], idxs)
    return _content_select(cfg, ingest)


def _load_gray(path: Path) -> np.ndarray:
    try:
        import cv2

        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        return img.astype(np.float32)
    except ImportError:
        from PIL import Image

        return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def _content_select(cfg: PipelineConfig, ingest: IngestResult) -> KeyframeResult:
    kept_idx: list[int] = []
    kept_paths: list[Path] = []
    prev: np.ndarray | None = None
    for i, p in enumerate(ingest.frame_paths):
        g = _load_gray(p)
        if prev is None or float(np.mean(np.abs(g - prev))) >= cfg.keyframe_threshold:
            kept_idx.append(i)
            kept_paths.append(p)
            prev = g
    # always keep the final frame so the end-state is reconstructable
    if ingest.frame_paths and kept_idx[-1] != len(ingest.frame_paths) - 1:
        kept_idx.append(len(ingest.frame_paths) - 1)
        kept_paths.append(ingest.frame_paths[-1])
    return KeyframeResult(kept_paths, kept_idx)
