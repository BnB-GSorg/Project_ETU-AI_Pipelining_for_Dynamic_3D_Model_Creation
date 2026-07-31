"""Stage 5 — Tracking: establish temporal correspondence ("cascade").

The brief: track changes across time with optical flow or learned deformation
fields, so the same part keeps its identity frame-to-frame. For the prototype
we estimate a rigid transform (rotation + translation) per part between
consecutive time slices via Kabsch on the segment centroids/points. The "deform"
backend (learned deformation field) is the GPU upgrade path.

Output: per part, a list of (t, position, quaternion) keyframes in world space —
exactly what the mmi-lite track needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mmi.pipeline.config import PipelineConfig
from mmi.stages.reconstruct import Reconstruction
from mmi.stages.segment import Segmentation


@dataclass
class PartTrack:
    part_id: int
    keyframes: list[dict] = field(default_factory=list)  # {t, position[3], quaternion[4]}


@dataclass
class Tracking:
    parts: list[PartTrack] = field(default_factory=list)


def run(cfg: PipelineConfig, recon: Reconstruction, seg: Segmentation) -> Tracking:
    if cfg.track_method == "deform":
        raise NotImplementedError(
            "Learned deformation-field tracking is the GPU path. See docs/ROADMAP.md M4."
        )
    return _rigid_track(recon, seg)


def _mat_to_quat(R: np.ndarray) -> np.ndarray:
    """Rotation matrix -> quaternion [x,y,z,w]."""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    else:
        i = np.argmax([R[0, 0], R[1, 1], R[2, 2]])
        if i == 0:
            s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
            w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
        elif i == 1:
            s = np.sqrt(1.0 - R[0, 0] + R[1, 1] - R[2, 2]) * 2
            w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
        else:
            s = np.sqrt(1.0 - R[0, 0] - R[1, 1] + R[2, 2]) * 2
            w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    return np.array([x, y, z, w])


def _kabsch(P: np.ndarray, Q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Best rigid transform mapping P onto Q. Returns (R, t)."""
    cp, cq = P.mean(0), Q.mean(0)
    H = (P - cp).T @ (Q - cq)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    return R, cq - R @ cp


def _rigid_track(recon: Reconstruction, seg: Segmentation) -> Tracking:
    parts = sorted(seg.layer_names) or [0]
    tracking = Tracking(parts=[PartTrack(pid) for pid in parts])
    by_id = {pt.part_id: pt for pt in tracking.parts}

    for ti, sl in enumerate(recon.slices):
        lab = seg.labels[ti] if ti < len(seg.labels) else np.zeros(len(sl.points), int)
        for pid in parts:
            mask = lab == pid
            if mask.sum() < 3:
                continue
            pts = sl.points[mask]
            if ti == 0:
                R, t = np.eye(3), np.zeros(3)
                by_id[pid]._ref = pts  # cache reference cloud for Kabsch
            else:
                ref = getattr(by_id[pid], "_ref", pts)
                m = min(len(ref), len(pts))
                R, t = _kabsch(ref[:m], pts[:m])
            by_id[pid].keyframes.append(
                {"t": sl.t, "position": (pts.mean(0)).tolist(), "quaternion": _mat_to_quat(R).tolist()}
            )
    return tracking
