"""Stage 3 — Reconstruction: keyframes -> per-time 3D geometry.

This is the heavy, GPU-bound stage and the research core of Person A's work.
Three backends are defined behind one interface so the rest of the pipeline
(segment / track / assemble / viewer) is backend-agnostic:

    colmap   : classic SfM + MVS. CPU-feasible (slow); good geometric baseline.
    3dgs     : 3D Gaussian Splatting per time-window (needs CUDA).
    dyn-nerf : Dynamic NeRF / 4D Gaussian Splatting -> renderable 4D directly.

Each backend returns a `Reconstruction`: a list of per-time point clouds in a
shared world frame. The neural backends are intentionally stubbed with the
exact call sites and expected artifacts documented, so they can be filled in on
the GPU box without touching downstream code.

To keep the prototype runnable end-to-end *today* (no GPU, maybe no COLMAP),
`backend="synthetic"` emits a placeholder point cloud so you can exercise the
whole pipeline and the viewer. Real runs use colmap/3dgs/dyn-nerf.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field

import numpy as np

from mmi.pipeline.config import PipelineConfig
from mmi.stages.keyframes import KeyframeResult


@dataclass
class TimeSlice:
    t: int                       # frame index this geometry corresponds to
    points: np.ndarray           # (N,3) world-space points
    colors: np.ndarray | None = None  # (N,3) in 0..1


@dataclass
class Reconstruction:
    slices: list[TimeSlice] = field(default_factory=list)
    backend: str = "synthetic"


def run(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    backend = cfg.recon_backend
    if backend == "colmap" and shutil.which("colmap"):
        return _run_colmap(cfg, keyframes)
    if backend in ("3dgs", "dyn-nerf"):
        return _run_neural(cfg, keyframes, backend)
    # Fallback keeps the prototype runnable without GPU/COLMAP installed.
    return _run_synthetic(cfg, keyframes)


# ---------------------------------------------------------------------------
# COLMAP baseline (CPU-feasible)
# ---------------------------------------------------------------------------
def _run_colmap(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Drive COLMAP feature-extract -> match -> mapper -> dense.

    NOTE: COLMAP reconstructs a *static* scene from multi-view images. For a
    moving process we run it per stable time-window (or treat the cube as rigid
    and recover camera trajectory). This function wires the CLI calls; the dense
    .ply is then loaded into TimeSlices. Left as a TODO to keep the prototype
    dependency-light — see docs/ROADMAP.md milestone M2.
    """
    raise NotImplementedError(
        "COLMAP backend wiring is stubbed. Steps: `colmap feature_extractor`, "
        "`exhaustive_matcher`, `mapper`, `image_undistorter`, `patch_match_stereo`, "
        "`stereo_fusion` -> load fused.ply into TimeSlices. See docs/ROADMAP.md M2."
    )


# ---------------------------------------------------------------------------
# Neural backends (GPU) — interface defined, training stubbed
# ---------------------------------------------------------------------------
def _run_neural(cfg: PipelineConfig, keyframes: KeyframeResult, backend: str) -> Reconstruction:
    """Train a (4D) Gaussian-splat / dynamic-NeRF model on the keyframes.

    Expected flow on the GPU box (see docs/ROADMAP.md M3):
      1. COLMAP for camera poses (sparse) — required init for 3DGS.
      2. Train splats:  modified-3DGS for static, 4D-GS / TFS-NeRV for dynamic.
      3. Optionally synthesize extra virtual views (Diffusion4D) to fill gaps.
      4. Export per-time point samples (or .splat) -> TimeSlices.
    The artifact contract: a checkpoint dir + sampled point clouds per frame.
    """
    raise NotImplementedError(
        f"Neural backend {backend!r} requires a CUDA GPU and a splat/NeRF trainer. "
        "Interface is fixed; training is filled in on the GPU box. See docs/ROADMAP.md M3."
    )


# ---------------------------------------------------------------------------
# Synthetic placeholder — keeps the whole pipeline + viewer exercisable now
# ---------------------------------------------------------------------------
def _run_synthetic(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    rng = np.random.default_rng(0)
    base = rng.uniform(-1.2, 1.2, size=(1500, 3))
    base = base[np.abs(base).max(axis=1) > 0.4]  # hollow-ish shell
    colors = (base - base.min(axis=0)) / (np.ptp(base, axis=0) + 1e-6)
    slices = []
    n = max(2, len(keyframes.keyframe_paths))
    for i in range(n):
        ang = 2 * np.pi * i / n
        rot = np.array([[np.cos(ang), 0, np.sin(ang)], [0, 1, 0], [-np.sin(ang), 0, np.cos(ang)]])
        slices.append(TimeSlice(t=i, points=base @ rot.T, colors=colors))
    return Reconstruction(slices=slices, backend="synthetic")
