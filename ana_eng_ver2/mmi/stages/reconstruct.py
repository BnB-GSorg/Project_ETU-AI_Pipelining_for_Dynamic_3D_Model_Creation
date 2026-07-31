"""Stage 3 — Reconstruction: keyframes -> per-time 3D geometry.

Three backends behind one interface:
  colmap   : classic SfM + MVS. CPU-feasible; requires COLMAP installed.
  gsplat     : 3D Gaussian Splatting per time-window (needs CUDA GPU + gsplat).
  dyn-nerf : Dynamic NeRF / 4D Gaussian Splatting (needs CUDA GPU).

Each returns a Reconstruction: a list of per-time point clouds in a
shared world frame.

Multi-view aware: when the ingest stage provides N>1 views, the
reconstruction combines all views for true 3D depth estimation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mmi.pipeline.config import PipelineConfig
from mmi.stages.keyframes import KeyframeResult


@dataclass
class TimeSlice:
    t: int
    points: np.ndarray           # (N,3) world-space points
    colors: np.ndarray | None = None  # (N,3) in 0..1


@dataclass
class Reconstruction:
    slices: list[TimeSlice] = field(default_factory=list)
    backend: str = "synthetic"


def run(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    backend = cfg.recon_backend
    if backend == "colmap":
        return _run_colmap(cfg, keyframes)
    if backend == "3dgs":
        return _run_gsplat(cfg, keyframes)
    if backend == "dyn-nerf":
        return _run_dyn_nerf(cfg, keyframes)
    # Fallback: synthetic placeholder
    return _run_synthetic(cfg, keyframes)


# ── COLMAP backend ──────────────────────────────────────────────────────

def _require_colmap():
    """Verify COLMAP is installed and on PATH."""
    if shutil.which("colmap") is None:
        raise RuntimeError(
            "COLMAP is not installed or not on PATH.\n"
            "Install: https://colmap.github.io/install.html\n"
            "  Ubuntu: sudo apt install colmap\n"
            "  macOS:  brew install colmap\n"
            "Or use --backend synthetic for a placeholder."
        )


def _run_colmap(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Run COLMAP SfM+MVS per time-window on multi-view keyframes.

    For each timepoint t:
      1. Collect the same-indexed frame from each camera view.
      2. Run COLMAP feature extraction + exhaustive matching + sparse mapper.
      3. Extract the sparse point cloud → TimeSlice.

    Multi-view frames are assumed to be synchronized: the same frame index
    across all views represents the same moment in time.
    """
    _require_colmap()

    n_views = len(cfg.get_videos()) if cfg.videos else 1
    slices: list[TimeSlice] = []

    # Resolve frame directories per view
    base_workdir = cfg.stage_dir("03_recon")
    view_dirs: dict[int, Path] = {}
    for vi in range(n_views):
        view_dir = cfg.workdir / f"01_frames/view_{vi:02d}"
        if not view_dir.exists():
            # Single-view: frames are directly in 01_frames
            view_dir = cfg.workdir / "01_frames"
        view_dirs[vi] = view_dir

    for t, _ in enumerate(keyframes.keyframe_paths):
        workspace = base_workdir / f"time_{t:04d}"
        img_dir = workspace / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        # Collect frame[t] from each view
        for vi in range(n_views):
            frames = sorted(view_dirs[vi].glob("frame_*.png"))
            if t >= len(frames):
                raise RuntimeError(
                    f"Frame index {t} out of range for view {vi} "
                    f"(has {len(frames)} frames). Views must be synchronized."
                )
            dest = img_dir / f"view{vi:02d}.png"
            shutil.copy(frames[t], dest)

        # ── COLMAP pipeline ──
        db_path = workspace / "database.db"
        sparse_dir = workspace / "sparse"

        subprocess.run([
            "colmap", "feature_extractor",
            "--database_path", str(db_path),
            "--image_path", str(img_dir),
            "--SiftExtraction.use_gpu", "1",
        ], check=True, capture_output=False)

        subprocess.run([
            "colmap", "exhaustive_matcher",
            "--database_path", str(db_path),
            "--SiftExtraction.use_gpu", "1",
        ], check=True, capture_output=False)

        sparse_dir.mkdir(exist_ok=True)
        subprocess.run([
            "colmap", "mapper",
            "--database_path", str(db_path),
            "--image_path", str(img_dir),
            "--output_path", str(sparse_dir),
        ], check=True, capture_output=False)

        # Load sparse reconstruction
        points, colors = _load_colmap_sparse(sparse_dir)
        slices.append(TimeSlice(t=t, points=points, colors=colors))

    return Reconstruction(slices=slices, backend="colmap")


def _load_colmap_sparse(sparse_dir: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Load the largest sparse model's points3D.bin from a COLMAP output directory.

    COLMAP may produce multiple models (0/, 1/, ...). We take the one with the
    most points (typically the successful reconstruction).
    """
    models = sorted(sparse_dir.glob("*/points3D.bin"))
    if not models:
        # Try direct points3D.bin
        direct = sparse_dir / "points3D.bin"
        if direct.exists():
            models = [direct]

    if not models:
        raise RuntimeError(
            f"No points3D.bin found in {sparse_dir}. COLMAP reconstruction may have failed."
        )

    # Pick the largest model
    best = max(models, key=lambda p: p.stat().st_size if p.is_file() else 0)
    return _read_colmap_points3d(best)


def _read_colmap_points3d(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Parse COLMAP points3D.bin binary format.

    Format (per point):
      point3D_id (uint64), x (double), y (double), z (double),
      r (uint8), g (uint8), b (uint8), error (double),
      track_length (uint64), [image_id (uint32), point2D_idx (uint32)] × track_length
    """
    data = path.read_bytes()
    import struct

    num_points = struct.unpack_from("<Q", data, 0)[0]
    offset = 8  # skip point count

    points = np.zeros((num_points, 3), dtype=np.float64)
    colors = np.zeros((num_points, 3), dtype=np.float32)

    for i in range(num_points):
        pid = struct.unpack_from("<Q", data, offset)[0]; offset += 8
        x = struct.unpack_from("<d", data, offset)[0]; offset += 8
        y = struct.unpack_from("<d", data, offset)[0]; offset += 8
        z = struct.unpack_from("<d", data, offset)[0]; offset += 8
        r = struct.unpack_from("<B", data, offset)[0]; offset += 1
        g = struct.unpack_from("<B", data, offset)[0]; offset += 1
        b = struct.unpack_from("<B", data, offset)[0]; offset += 1
        error = struct.unpack_from("<d", data, offset)[0]; offset += 8
        track_len = struct.unpack_from("<Q", data, offset)[0]; offset += 8
        # Skip track entries
        offset += track_len * 8  # 4+4 bytes per track entry

        points[i] = [x, y, z]
        colors[i] = [r / 255.0, g / 255.0, b / 255.0]

    return points, colors


# ── 3D Gaussian Splatting backend ───────────────────────────────────────

def _check_gpu() -> bool:
    """Check if a CUDA GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _run_gsplat(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Train 3D Gaussian Splatting per time-window using gsplat.

    Requires: CUDA GPU, gsplat (pip install gsplat), colmap (for init)

    Process per time-window:
      1. COLMAP for camera poses (sparse init)
      2. Train 3DGS model on multi-view images
      3. Export point cloud from trained Gaussians:
         filter by opacity threshold, use mean positions as points,
         spherical harmonics SH₀ as base colors.
    """
    if not _check_gpu():
        raise RuntimeError(
            "3DGS backend requires a CUDA GPU.\n"
            "No CUDA device found. Use --backend colmap for CPU baseline,\n"
            "or --backend synthetic for a placeholder."
        )

    _require_colmap()
    try:
        import gsplat  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "gsplat is not installed. Install with: pip install gsplat\n"
            "See: https://docs.gsplat.studio/"
        )

    slices: list[TimeSlice] = []
    n_views = len(cfg.get_videos()) if cfg.videos else 1
    base_workdir = cfg.stage_dir("03_recon")

    for t, _ in enumerate(keyframes.keyframe_paths):
        workspace = base_workdir / f"gsplat_time_{t:04d}"
        workspace.mkdir(parents=True, exist_ok=True)
        img_dir = workspace / "images"
        img_dir.mkdir(exist_ok=True)

        # Collect synchronized frames from all views
        view_dirs = _resolve_view_dirs(cfg, n_views)
        for vi in range(n_views):
            frames = sorted(view_dirs[vi].glob("frame_*.png"))
            if t >= len(frames):
                raise RuntimeError(f"Frame {t} out of range for view {vi}")
            shutil.copy(frames[t], img_dir / f"view{vi:02d}.png")

        # ── Step 1: COLMAP sparse init ──
        colmap_workspace = workspace / "colmap"
        colmap_workspace.mkdir(exist_ok=True)
        db_path = colmap_workspace / "database.db"
        sparse_dir = colmap_workspace / "sparse"

        _run_colmap_sparse(img_dir, db_path, sparse_dir)

        # ── Step 2: Train 3DGS ──
        # The gsplat training API varies by version. We use the CLI approach
        # which is the most stable interface.
        checkpoint_dir = workspace / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        subprocess.run([
            "python", "-m", "gsplat.train",
            "--data_dir", str(colmap_workspace),
            "--result_dir", str(checkpoint_dir),
            "--max_steps", "7000",
        ], check=True, capture_output=False)

        # ── Step 3: Export point cloud ──
        points, colors = _export_gsplat_pointcloud(checkpoint_dir)
        slices.append(TimeSlice(t=t, points=points, colors=colors))

    return Reconstruction(slices=slices, backend="3dgs")


def _run_colmap_sparse(img_dir: Path, db_path: Path, sparse_dir: Path):
    """Run COLMAP sparse reconstruction only (for 3DGS initialization)."""
    subprocess.run([
        "colmap", "feature_extractor",
        "--database_path", str(db_path), "--image_path", str(img_dir),
        "--SiftExtraction.use_gpu", "1",
    ], check=True)
    subprocess.run([
        "colmap", "exhaustive_matcher",
        "--database_path", str(db_path), "--SiftExtraction.use_gpu", "1",
    ], check=True)
    sparse_dir.mkdir(exist_ok=True)
    subprocess.run([
        "colmap", "mapper",
        "--database_path", str(db_path), "--image_path", str(img_dir),
        "--output_path", str(sparse_dir),
    ], check=True)


def _export_gsplat_pointcloud(checkpoint_dir: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Export point cloud from a trained 3DGS checkpoint.

    Loads the Gaussian parameters, filters by opacity, and returns
    mean positions and base colors (SH₀ term).
    """
    import torch

    ckpt_files = sorted(checkpoint_dir.glob("*.pt"))
    if not ckpt_files:
        ckpt_files = sorted(checkpoint_dir.glob("*.pth"))
    if not ckpt_files:
        raise RuntimeError(f"No checkpoint found in {checkpoint_dir}")

    ckpt = torch.load(ckpt_files[-1], map_location="cpu", weights_only=True)

    # gsplat stores: means (N,3), opacities (N,), scales (N,3),
    # quats (N,4), sh_coeffs (N, (sh_degree+1)², 3)
    means = ckpt.get("means", ckpt.get("xyz"))
    opacities = ckpt.get("opacities", ckpt.get("opacity"))
    sh = ckpt.get("sh_coeffs", ckpt.get("features_dc"))

    if means is None:
        raise RuntimeError(f"Checkpoint does not contain Gaussian means. Keys: {list(ckpt.keys())}")

    means = means.detach().cpu().numpy() if hasattr(means, "detach") else np.array(means)

    # Filter by opacity
    if opacities is not None:
        opacity = opacities.detach().cpu().numpy() if hasattr(opacities, "detach") else np.array(opacities)
        opacity = opacity.squeeze()
        mask = opacity > 0.1
        means = means[mask]

    # Extract base color (SH₀)
    colors = None
    if sh is not None:
        sh_np = sh.detach().cpu().numpy() if hasattr(sh, "detach") else np.array(sh)
        # SH₀ is the first coefficient → base color
        if sh_np.ndim == 3:
            base_color = sh_np[:, 0, :]  # (N, 3)
        else:
            base_color = sh_np[:, :3]
        if "mask" in dir() and mask is not None:
            base_color = base_color[mask]
        # SH colors can be negative; normalize to [0,1]
        colors = (base_color - base_color.min()) / (base_color.max() - base_color.min() + 1e-6)

    return means.astype(np.float64), colors.astype(np.float32) if colors is not None else None


# ── Dynamic NeRF backend ────────────────────────────────────────────────

def _run_dyn_nerf(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Train a dynamic NeRF / 4D Gaussian Splatting model.

    Unlike per-window 3DGS, this trains a single model that captures the
    entire temporal sequence, outputting per-frame point clouds.

    Requires: CUDA GPU with sufficient VRAM, nerfstudio or similar.
    """
    if not _check_gpu():
        raise RuntimeError(
            "Dynamic NeRF backend requires a CUDA GPU.\n"
            "No CUDA device found. Use --backend colmap or --backend 3dgs."
        )
    raise NotImplementedError(
        "Dynamic NeRF / 4DGS backend is not yet implemented.\n"
        "Use --backend 3dgs for per-window static Gaussian splatting,\n"
        "or --backend colmap for CPU baseline."
    )


# ── Helpers ─────────────────────────────────────────────────────────────

def _resolve_view_dirs(cfg: PipelineConfig, n_views: int) -> dict[int, Path]:
    """Find the frame directories for each view."""
    dirs = {}
    for vi in range(n_views):
        d = cfg.workdir / f"01_frames/view_{vi:02d}"
        if not d.exists():
            d = cfg.workdir / "01_frames"
        dirs[vi] = d
    return dirs


# ── Synthetic (fallback) ────────────────────────────────────────────────

def _run_synthetic(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Placeholder point cloud for exercising the pipeline without real data."""
    rng = np.random.default_rng(0)
    base = rng.uniform(-1.2, 1.2, size=(1500, 3))
    base = base[np.abs(base).max(axis=1) > 0.4]  # hollow shell
    colors = (base - base.min(axis=0)) / (np.ptp(base, axis=0) + 1e-6)
    slices = []
    n = max(2, len(keyframes.keyframe_paths))
    for i in range(n):
        ang = 2 * np.pi * i / n
        rot = np.array([
            [np.cos(ang), 0, np.sin(ang)],
            [0, 1, 0],
            [-np.sin(ang), 0, np.cos(ang)],
        ])
        slices.append(TimeSlice(t=i, points=base @ rot.T, colors=colors))
    return Reconstruction(slices=slices, backend="synthetic")
