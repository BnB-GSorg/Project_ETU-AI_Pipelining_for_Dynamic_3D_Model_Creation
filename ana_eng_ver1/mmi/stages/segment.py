"""Stage 4 — Segmentation: split reconstructed geometry into parts/layers.

The brief calls for "segment colored parts for better handling of overlaps".
"color" mode clusters points by hue and is fully runnable now. "sam" mode
(Segment-Anything in 3D / lifted 2D masks) is the GPU upgrade path.

Output: a per-point integer label per TimeSlice, plus a label->layer mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mmi.pipeline.config import PipelineConfig
from mmi.stages.reconstruct import Reconstruction


@dataclass
class Segmentation:
    labels: list[np.ndarray] = field(default_factory=list)  # one (N,) array per TimeSlice
    layer_names: dict[int, str] = field(default_factory=dict)


def run(cfg: PipelineConfig, recon: Reconstruction) -> Segmentation:
    if cfg.segmenter == "sam":
        raise NotImplementedError(
            "SAM segmentation (lifted 2D masks -> 3D) is the GPU path. See docs/ROADMAP.md M4."
        )
    return _color_segment(recon)


def _color_segment(recon: Reconstruction, k: int = 6) -> Segmentation:
    """Cheap k-means on RGB to group colored parts (no sklearn dependency)."""
    seg = Segmentation()
    centers = None
    for sl in recon.slices:
        if sl.colors is None:
            seg.labels.append(np.zeros(len(sl.points), dtype=int))
            continue
        c = sl.colors
        if centers is None:
            idx = np.linspace(0, len(c) - 1, k).astype(int)
            centers = c[idx].copy()
        for _ in range(8):  # a few Lloyd iterations, shared centers across time
            d = ((c[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
            lab = d.argmin(1)
            for j in range(k):
                if (lab == j).any():
                    centers[j] = c[lab == j].mean(0)
        seg.labels.append(lab)
    seg.layer_names = {j: f"part_{j}" for j in range(k)}
    return seg
