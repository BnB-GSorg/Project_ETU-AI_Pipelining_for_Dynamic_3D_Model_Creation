"""Stage 7 — Encode reconstruction output into mmi-git format.

Takes the pipeline's Reconstruction + Segmentation + Tracking output and
produces an MmiGitScene: base point cloud (frame 0) + commit chain of
whole-scene 4×4 transform matrices + periodic keyframes for fast seeking.

This is the bridge between the classic reconstruction pipeline and the
new git-like delta storage format.
"""

from __future__ import annotations

import numpy as np

from mmi.formats.mmi_git import (
    MmiGitScene, PartSpec, Commit, KeyFrame, GitGeometry,
    identity_matrix, KEYFRAME_INTERVAL,
)
from mmi.stages.reconstruct import Reconstruction, TimeSlice
from mmi.stages.segment import Segmentation
from mmi.stages.track import Tracking, PartTrack


# ── Quaternion math (same as converter, kept local for modularity) ──────

def _quat_multiply(q1: list[float], q2: list[float]) -> list[float]:
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ]


def _quat_inverse(q: list[float]) -> list[float]:
    return [-q[0], -q[1], -q[2], q[3]]


def _quat_to_matrix(q: list[float]) -> np.ndarray:
    """Quaternion [x,y,z,w] → 4×4 rotation matrix."""
    x, y, z, w = q
    return np.array([
        [1-2*y*y-2*z*z, 2*x*y-2*z*w,   2*x*z+2*y*w,   0],
        [2*x*y+2*z*w,   1-2*x*x-2*z*z, 2*y*z-2*x*w,   0],
        [2*x*z-2*y*w,   2*y*z+2*x*w,   1-2*x*x-2*y*y, 0],
        [0,             0,             0,             1],
    ], dtype=np.float64)


def _build_abs_matrix(position: list[float], quaternion: list[float]) -> np.ndarray:
    """Build absolute 4×4 homogeneous transform from position + quaternion."""
    R = _quat_to_matrix(quaternion)
    T = np.eye(4, dtype=np.float64)
    T[0, 3] = position[0]
    T[1, 3] = position[1]
    T[2, 3] = position[2]
    return T @ R


def _relative_matrix(
    prev_pos: list[float], prev_quat: list[float],
    curr_pos: list[float], curr_quat: list[float],
) -> list[float]:
    """Compute relative 4×4 transform: inv(prev) * curr → flat list of 16."""
    M_prev = _build_abs_matrix(prev_pos, prev_quat)
    M_curr = _build_abs_matrix(curr_pos, curr_quat)
    M_rel = np.linalg.inv(M_prev) @ M_curr
    return M_rel.flatten().tolist()


# ── Main encoder ────────────────────────────────────────────────────────

def encode(
    recon: Reconstruction,
    seg: Segmentation,
    tracking: Tracking,
    title: str = "Reconstructed Process",
    fps: int = 10,
    generate_kfs: bool = True,
) -> MmiGitScene:
    """Convert pipeline output to mmi-git format.

    Args:
        recon: Reconstruction with per-frame TimeSlices (point clouds).
        seg: Segmentation — per-slice per-point integer labels.
        tracking: Tracking — per-part keyframes {t, position, quaternion}.
        title: Scene title for metadata.
        fps: Playback frames per second.
        generate_kfs: If True, pre-compute keyframes for O(1) seeking.

    Returns:
        MmiGitScene ready for save/playback.
    """
    if not recon.slices:
        raise ValueError("Empty reconstruction — cannot encode")

    duration = len(recon.slices)

    # ── 1. Base geometry (frame 0) ──
    base_slice = recon.slices[0]
    base_points = base_slice.points.flatten().tolist() if base_slice.points.size else []
    base_colors = base_slice.colors.flatten().tolist() if base_slice.colors is not None else None

    # ── 2. Parts from segmentation ──
    parts: list[PartSpec] = []
    for pid in sorted(seg.layer_names):
        if seg.labels:
            mask = seg.labels[0] == pid
            indices = [int(i) for i, m in enumerate(mask) if m]
        else:
            indices = list(range(len(base_slice.points)))
        if not indices:
            continue
        parts.append(PartSpec(
            id=f"part_{pid:02d}",
            label=seg.layer_names.get(pid, f"part_{pid:02d}"),
            point_indices=indices,
            geometry=GitGeometry(kind="pointcloud"),
        ))

    # ── 3. Commits from tracking ──
    # Group per-part keyframes by frame index
    by_frame: dict[int, dict[str, dict]] = {}
    for pt in tracking.parts:
        part_id = f"part_{pt.part_id:02d}"
        sorted_kfs = sorted(pt.keyframes, key=lambda k: k["t"])

        for i in range(len(sorted_kfs)):
            kf = sorted_kfs[i]
            t = kf["t"]
            if t not in by_frame:
                by_frame[t] = {}
            by_frame[t][part_id] = {
                "position": kf["position"],
                "quaternion": kf["quaternion"],
            }

    # Build relative commits
    commits: list[Commit] = []
    prev_poses: dict[str, dict] = {}  # part_id → {position, quaternion} from previous frame

    for t in sorted(by_frame):
        frame_poses = by_frame[t]
        transforms: dict[str, list[float]] = {}

        for part_id, curr_pose in frame_poses.items():
            if part_id in prev_poses:
                # Delta from previous to current
                delta = _relative_matrix(
                    prev_poses[part_id]["position"],
                    prev_poses[part_id]["quaternion"],
                    curr_pose["position"],
                    curr_pose["quaternion"],
                )
                transforms[part_id] = delta
            else:
                # First appearance — no previous to diff against
                # Use absolute transform from origin
                abs_mat = _build_abs_matrix(curr_pose["position"], curr_pose["quaternion"])
                transforms[part_id] = abs_mat.flatten().tolist()

        # Fill identity for parts not present at this frame
        for part in parts:
            if part.id not in transforms:
                transforms[part.id] = identity_matrix()

        commits.append(Commit(t=t, transforms=transforms))
        prev_poses = {pid: dict(pose) for pid, pose in frame_poses.items()}

    # ── 4. Build scene ──
    scene = MmiGitScene(
        title=title,
        fps=fps,
        duration_frames=duration,
        base_points=base_points,
        base_colors=base_colors,
        parts=parts,
        commits=commits,
        source=f"reconstruction:{recon.backend}",
    )

    # ── 5. Generate keyframes if requested ──
    if generate_kfs:
        scene.generate_keyframes()

    return scene


# ── Synthetic test helper ───────────────────────────────────────────────

def encode_synthetic(n_frames: int = 20, n_points: int = 300, n_parts: int = 2) -> MmiGitScene:
    """Create a synthetic mmi-git scene for testing without real data.

    Generates a rotating + translating point cloud with simple rigid motion
    so the format and viewer can be exercised end-to-end.
    """
    rng = np.random.default_rng(42)

    # Base cloud: random points in [-2, 2]³
    base_pts = rng.uniform(-2, 2, size=(n_points, 3))
    base_colors = (base_pts - base_pts.min(axis=0)) / (np.ptp(base_pts, axis=0) + 1e-6)

    # Split into parts
    pts_per_part = n_points // n_parts
    parts = []
    for pid in range(n_parts):
        start = pid * pts_per_part
        end = start + pts_per_part if pid < n_parts - 1 else n_points
        parts.append(PartSpec(
            id=f"part_{pid:02d}",
            label=f"Part {pid}",
            point_indices=list(range(start, end)),
            geometry=GitGeometry(kind="pointcloud", point_size=0.03),
            color=f"#{pid*70%256:02x}{(pid*130)%256:02x}{(255-pid*50)%256:02x}",
        ))

    # Generate commits: each part rotates and translates
    commits = []
    identity = identity_matrix()
    for t in range(n_frames - 1):
        angle = 2 * np.pi * t / (n_frames - 1)
        transforms = {}
        for pid in range(n_parts):
            offset = pid * np.pi / n_parts
            # Rotation around Y + translation along X
            ca, sa = np.cos(angle + offset), np.sin(angle + offset)
            T = [
                ca, 0, sa, 0.1 * t,
                0,  1, 0,  0,
                -sa,0, ca, 0.05 * pid * t,
                0,  0, 0,  1,
            ]
            transforms[f"part_{pid:02d}"] = T
        commits.append(Commit(t=t, transforms=transforms))

    scene = MmiGitScene(
        title="Synthetic reconstruction test",
        fps=10,
        duration_frames=n_frames,
        base_points=base_pts.flatten().tolist(),
        base_colors=base_colors.flatten().tolist(),
        parts=parts,
        commits=commits,
        source="synthetic",
    )
    scene.generate_keyframes()
    return scene
