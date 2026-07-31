#!/usr/bin/env python3
"""Convert mmi-lite scenes to mmi-git format.

    python scripts/mmi_convert.py data/samples/fourier_stack.json --out data/samples/fourier_stack.mmi
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.formats.mmi_git import MmiGitScene, PartSpec, Commit, KeyFrame, KEYFRAME_INTERVAL, GitGeometry
from mmi.formats.mmi_scene import Scene as LiteScene, PointCloudGeometry


def _quat_multiply(q1: list[float], q2: list[float]) -> list[float]:
    """Multiply two quaternions [x,y,z,w]."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ]


def _quat_inverse(q: list[float]) -> list[float]:
    """Inverse of a unit quaternion [x,y,z,w]."""
    return [-q[0], -q[1], -q[2], q[3]]


def _quat_to_matrix(q: list[float]) -> list[float]:
    """Convert quaternion [x,y,z,w] to 4x4 rotation matrix (row-major, translation=0)."""
    x, y, z, w = q
    return [
        1-2*y*y-2*z*z, 2*x*y-2*z*w,   2*x*z+2*y*w,   0.0,
        2*x*y+2*z*w,   1-2*x*x-2*z*z, 2*y*z-2*x*w,   0.0,
        2*x*z-2*y*w,   2*y*z+2*x*w,   1-2*x*x-2*y*y, 0.0,
        0.0,           0.0,           0.0,           1.0,
    ]


def _build_transform(position: list[float], quaternion: list[float]) -> list[float]:
    """Build a 4x4 homogeneous transform from position and quaternion (row-major)."""
    R = np.array(_quat_to_matrix(quaternion), dtype=np.float64).reshape(4, 4)
    T = np.eye(4, dtype=np.float64)
    T[0, 3] = position[0]
    T[1, 3] = position[1]
    T[2, 3] = position[2]
    M = (T @ R).flatten().tolist()
    return M


def _relative_transform(
    prev_pos: list[float], prev_quat: list[float],
    curr_pos: list[float], curr_quat: list[float],
) -> list[float]:
    """Compute the delta transform from previous absolute pose to current absolute pose.

    If P_prev and P_curr are the absolute transforms, the relative transform is:
        P_rel = P_prev^{-1} * P_curr
    """
    # Build absolute matrices
    T_prev = _build_transform(prev_pos, prev_quat)
    T_curr = _build_transform(curr_pos, curr_quat)

    M_prev = np.array(T_prev, dtype=np.float64).reshape(4, 4)
    M_curr = np.array(T_curr, dtype=np.float64).reshape(4, 4)

    # Relative = inv(prev) * curr
    M_rel = np.linalg.inv(M_prev) @ M_curr
    return M_rel.flatten().tolist()


def lite_to_git(lite_dict: dict) -> MmiGitScene:
    """Convert mmi-lite JSON to mmi-git format.

    Strategy:
    - The base point cloud is the union of all object geometries at frame 0.
    - Each object becomes a PartSpec.
    - For each object, its track keyframes are converted to relative delta commits.
    - Commits are grouped by frame index (whole-scene).
    - Periodic keyframes are generated for random access.
    """
    # Parse lite scene
    meta = lite_dict.get("meta", {})
    lite_objects = lite_dict.get("objects", [])
    lite_layers = lite_dict.get("layers", [])

    title = meta.get("title", "Converted scene")
    fps = int(meta.get("fps", 12))
    duration = int(meta.get("duration_frames", 1))

    # ── Collect all object geometries into base ──
    base_points: list[float] = []
    base_colors: list[float] = []
    parts: list[PartSpec] = []

    for obj in lite_objects:
        geom = obj.get("geometry", {})
        kind = geom.get("kind", "pointcloud")
        obj_id = str(obj.get("id", f"obj_{len(parts)}"))

        if kind == "pointcloud":
            obj_pts = geom.get("points", [])
            if not obj_pts:
                continue
            start_idx = len(base_points) // 3
            n_pts = len(obj_pts) // 3
            base_points.extend(obj_pts)
            obj_cols = geom.get("colors", [])
            if obj_cols:
                base_colors.extend(obj_cols)
            git_geom = GitGeometry(kind="pointcloud", point_size=float(geom.get("point_size", 0.02)))
            parts.append(PartSpec(
                id=obj_id, label=obj_id,
                point_indices=list(range(start_idx, start_idx + n_pts)),
                geometry=git_geom,
            ))

        elif kind == "box":
            git_geom = GitGeometry(
                kind="box",
                size=geom.get("size", [1, 1, 1]),
                face_colors=geom.get("face_colors", {}),
            )
            parts.append(PartSpec(id=obj_id, label=obj_id, geometry=git_geom))

        elif kind == "surface":
            git_geom = GitGeometry(
                kind="surface",
                rows=int(geom.get("rows", 2)),
                cols=int(geom.get("cols", 2)),
                positions=geom.get("positions"),
                surface_colors=geom.get("colors"),
                surface_color=geom.get("color"),
                opacity=float(geom.get("opacity", 1.0)),
                wireframe=bool(geom.get("wireframe", False)),
            )
            parts.append(PartSpec(id=obj_id, label=obj_id, geometry=git_geom))

        elif kind == "line":
            obj_pts = geom.get("points") or geom.get("positions", [])
            git_geom = GitGeometry(
                kind="line",
                positions=obj_pts,
                surface_color=geom.get("color"),
                line_width=float(geom.get("width", 2.0)),
            )
            parts.append(PartSpec(id=obj_id, label=obj_id, geometry=git_geom))

        else:
            # Unknown kind — skip
            continue

    # ── Convert tracks to commits ──
    # Collect all (t, part_id, delta_matrix) across all objects
    deltas: list[tuple[int, str, list[float]]] = []

    for part, obj in zip(parts, lite_objects):
        track = obj.get("track", [])
        if not track:
            continue

        sorted_kfs = sorted(track, key=lambda k: k["t"])
        # First keyframe → base (no commit, geometry is at local origin)
        # Subsequent keyframes → delta relative to previous
        for i in range(1, len(sorted_kfs)):
            prev = sorted_kfs[i - 1]
            curr = sorted_kfs[i]
            delta = _relative_transform(
                prev.get("position", [0, 0, 0]),
                prev.get("quaternion", [0, 0, 0, 1]),
                curr.get("position", [0, 0, 0]),
                curr.get("quaternion", [0, 0, 0, 1]),
            )
            deltas.append((curr["t"], part.id, delta))

    # Group by frame → Commit
    commits_by_t: dict[int, dict[str, list[float]]] = {}
    for t, pid, delta in sorted(deltas, key=lambda x: x[0]):
        if t not in commits_by_t:
            commits_by_t[t] = {}
        commits_by_t[t][pid] = delta

    # Fill identity transforms for parts that don't change at this frame
    part_ids = {p.id for p in parts}
    identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    for t in commits_by_t:
        for pid in part_ids:
            if pid not in commits_by_t[t]:
                commits_by_t[t][pid] = identity

    commits = [Commit(t, tforms) for t, tforms in sorted(commits_by_t.items())]

    # ── Build layers ──
    layers = [{"id": l.get("id", ""), "name": l.get("name", ""),
               "color": l.get("color", "#888"), "visible": l.get("visible", True)}
              for l in lite_layers]

    scene = MmiGitScene(
        title=title, fps=fps, duration_frames=duration,
        base_points=base_points,
        base_colors=base_colors if base_colors else None,
        parts=parts, commits=commits,
        layers=layers,
        events=meta.get("events", []),
        source=f"converted:{meta.get('source', 'unknown')}",
    )

    # Generate keyframes for fast seeking
    scene.generate_keyframes()

    return scene


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert mmi-lite ↔ mmi-git")
    ap.add_argument("input", type=Path, help="mmi-lite .json file")
    ap.add_argument("--out", type=Path, required=True, help="output .mmi file")
    ap.add_argument("--no-keyframes", action="store_true", help="skip keyframe generation")
    args = ap.parse_args()

    print(f"Reading {args.input} ...")
    lite = json.loads(args.input.read_text())

    if lite.get("format") != "mmi-lite":
        print(f"Warning: input format is {lite.get('format')!r}, expected 'mmi-lite'")

    print(f"Converting: {lite['meta'].get('title')} ({len(lite.get('objects',[]))} objects, "
          f"{lite['meta'].get('duration_frames')} frames) ...")

    git = lite_to_git(lite)

    if not args.no_keyframes:
        print(f"Generated {git.keyframe_count} keyframes")

    probs = git.validate()
    if probs:
        print(f"Validation warnings ({len(probs)}):")
        for p in probs:
            print(f"  - {p}")
    else:
        print("Validation: clean")

    git.save(args.out)
    size_kb = args.out.stat().st_size / 1024
    print(f"Saved → {args.out} ({size_kb:.1f} KB, {git.part_count} parts, "
          f"{git.commit_count} commits, {git.total_points} base points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
