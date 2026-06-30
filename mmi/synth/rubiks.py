"""
Synthetic Rubik's-cube process generator.

Produces an ``mmi-lite`` Scene of a cube going through a sequence of moves.
This is the demo subject from the project brief (a "detailed visual explanation
to solve a Rubik's cube ... different view of the cube at different time
points"). It also serves as ground-truth target geometry/topology that the
reconstruction pipeline must eventually recover from a real video.

No external deps beyond numpy. Quaternion math is implemented inline.
"""

from __future__ import annotations

import math

import numpy as np

from mmi.formats.mmi_scene import (
    Annotation,
    BoxGeometry,
    Keyframe,
    Layer,
    Scene,
    SceneObject,
)

# Standard Western color scheme. Internal (hidden) faces are near-black.
COLORS = {
    "px": "#B71234",  # Right  -> red
    "nx": "#FF5800",  # Left   -> orange
    "py": "#FFFFFF",  # Up     -> white
    "ny": "#FFD500",  # Down   -> yellow
    "pz": "#009B48",  # Front  -> green
    "nz": "#0046AD",  # Back   -> blue
}
INTERNAL = "#161616"

# Move table: name -> (axis_vector, layer_axis_index, layer_value, angle_deg)
# Angle sign chosen for visually plausible standard-notation turns.
AXES = {"x": np.array([1.0, 0, 0]), "y": np.array([0, 1.0, 0]), "z": np.array([0, 0, 1.0])}
MOVES = {
    "U": ("y", 1, -90), "U'": ("y", 1, 90),
    "D": ("y", -1, 90), "D'": ("y", -1, -90),
    "R": ("x", 1, -90), "R'": ("x", 1, 90),
    "L": ("x", -1, 90), "L'": ("x", -1, -90),
    "F": ("z", 1, -90), "F'": ("z", 1, 90),
    "B": ("z", -1, 90), "B'": ("z", -1, -90),
}

# ---------------------------------------------------------------------------
# quaternion helpers (xyzw order, matching Three.js)
# ---------------------------------------------------------------------------


def quat_from_axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    s = math.sin(angle_rad / 2)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle_rad / 2)])


def quat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ])


def quat_rotate_vec(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    qx, qy, qz, qw = q
    u = np.array([qx, qy, qz])
    return 2 * np.dot(u, v) * u + (qw * qw - np.dot(u, u)) * v + 2 * qw * np.cross(u, v)


# ---------------------------------------------------------------------------
# cube model
# ---------------------------------------------------------------------------


class _Cubie:
    def __init__(self, home: np.ndarray):
        self.home = home.astype(float)        # solved-state lattice position
        self.pos = home.astype(float)         # current position (rotates over time)
        self.quat = np.array([0.0, 0, 0, 1])  # current orientation

    @property
    def layer(self) -> str:
        nonzero = int(np.count_nonzero(np.round(self.home)))
        return {3: "corners", 2: "edges", 1: "centers", 0: "core"}[nonzero]

    def face_colors(self) -> dict[str, str]:
        # Colors fixed in the cubie's *local* frame, derived from the home cell.
        x, y, z = np.round(self.home).astype(int)
        return {
            "px": COLORS["px"] if x == 1 else INTERNAL,
            "nx": COLORS["nx"] if x == -1 else INTERNAL,
            "py": COLORS["py"] if y == 1 else INTERNAL,
            "ny": COLORS["ny"] if y == -1 else INTERNAL,
            "pz": COLORS["pz"] if z == 1 else INTERNAL,
            "nz": COLORS["nz"] if z == -1 else INTERNAL,
        }


def build_scene(
    moves: list[str] | None = None,
    frames_per_move: int = 9,
    pause_frames: int = 2,
    fps: int = 30,
    title: str = "Rubik's Cube — process demo",
) -> Scene:
    """Generate an mmi-lite Scene of the given move sequence."""
    if moves is None:
        moves = ["R", "U", "R'", "U'", "F", "R", "F'", "L'", "U", "D'", "B", "R'"]

    cubies = [
        _Cubie(np.array([x, y, z]))
        for x in (-1, 0, 1)
        for y in (-1, 0, 1)
        for z in (-1, 0, 1)
    ]
    ids = {id(c): f"cubie_{i:02d}" for i, c in enumerate(cubies)}

    tracks: dict[int, list[Keyframe]] = {id(c): [Keyframe(0, c.pos.tolist())] for c in cubies}
    events: list[dict] = []
    annotations: list[Annotation] = []

    frame = 0
    for move_idx, move in enumerate(moves):
        axis_key, layer_val, angle_deg = MOVES[move]
        axis = AXES[axis_key]
        axis_i = "xyz".index(axis_key)

        # cubies whose current cell lies in the turning layer
        turning = [c for c in cubies if round(c.pos[axis_i]) == layer_val]

        # snapshot start state so the arc is computed from a clean base
        start = {id(c): (c.pos.copy(), c.quat.copy()) for c in turning}
        events.append({"t": frame, "label": f"Move {move_idx + 1}: {move}"})

        for step in range(1, frames_per_move + 1):
            frame += 1
            frac = step / frames_per_move
            dq = quat_from_axis_angle(axis, math.radians(angle_deg) * frac)
            for c in turning:
                p0, q0 = start[id(c)]
                c.pos = quat_rotate_vec(dq, p0)
                c.quat = quat_mul(dq, q0)
                tracks[id(c)].append(Keyframe(frame, c.pos.tolist(), c.quat.tolist()))

        # snap to clean integer state to avoid float drift accumulating
        for c in turning:
            c.pos = np.round(c.pos)

        # 3D annotation pin marking the completed move, above the cube
        annotations.append(
            Annotation(t=frame, position=[0, 2.6, 0], text=move, t_end=frame + frames_per_move)
        )

        for _ in range(pause_frames):
            frame += 1
            for c in turning:
                tracks[id(c)].append(Keyframe(frame, c.pos.tolist(), c.quat.tolist()))

    duration = frame + 1

    layers = [
        Layer("corners", "Corners (8)", "#B71234"),
        Layer("edges", "Edges (12)", "#009B48"),
        Layer("centers", "Centers (6)", "#FFD500"),
        Layer("core", "Core (1)", "#161616"),
    ]

    objects = []
    for c in cubies:
        objects.append(
            SceneObject(
                id=ids[id(c)],
                geometry=BoxGeometry(size=[0.94, 0.94, 0.94], face_colors=c.face_colors()),
                track=tracks[id(c)],
                layer=c.layer,
            )
        )

    return Scene(
        title=title,
        fps=fps,
        duration_frames=duration,
        objects=objects,
        layers=layers,
        annotations=annotations,
        events=events,
        source="synthetic",
    )
