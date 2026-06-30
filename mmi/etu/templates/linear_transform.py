"""Template: linear_transform — a matrix as a 3D action on space.

ETU intent: a matrix written as a grid of numbers is opaque. Here a lattice of
points and the basis vectors morph from the identity to the matrix, so you can
*see* the transformation (shear, rotation, scaling, reflection, projection) and
how it warps space. Determinant = how volume scales (negative = orientation flip).

params:
    matrix : "shear" | "scale" | "rotation" | "reflection" | "projection" | "shear3d"
             (default "shear")
    n      : lattice points per axis (n^3 points)            (default 5)
    frames : timeline length                                 (default 70)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.templates.vector_field import _arrow_points
from mmi.formats.mmi_scene import (
    Keyframe,
    Layer,
    LineGeometry,
    PointCloudGeometry,
    Scene,
    SceneObject,
)

_c, _s = np.cos(np.pi / 4), np.sin(np.pi / 4)
_MATRICES = {
    "shear": np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]], float),
    "scale": np.array([[1.6, 0, 0], [0, 0.6, 0], [0, 0, 1]], float),
    "rotation": np.array([[_c, -_s, 0], [_s, _c, 0], [0, 0, 1]], float),
    "reflection": np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]], float),
    "projection": np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]], float),  # singular, det 0
    "shear3d": np.array([[1, 0.5, 0.3], [0, 1, 0.4], [0, 0, 1]], float),
}
_AXIS_COLORS = ["#ff5b5b", "#37c98a", "#5b8cff"]


def build(params: dict) -> Scene:
    name = params.get("matrix", "shear")
    n = int(params.get("n", 5))
    nframes = int(params.get("frames", 70))
    M = _MATRICES.get(name, _MATRICES["shear"])
    det = float(np.linalg.det(M))

    coords = np.linspace(-1, 1, n)
    pts = np.array([[x, y, z] for x in coords for y in coords for z in coords])
    S = 1.8
    base = pts * S
    transformed = (pts @ M.T) * S
    cols = ((pts + 1) / 2).flatten().tolist()           # color by original cell

    hold = max(1, nframes // 5)
    lattice = SceneObject(
        id="lattice",
        geometry=PointCloudGeometry(
            points=base.flatten().tolist(), colors=cols, point_size=0.06,
            frames=[
                {"t": 0, "positions": base.flatten().tolist(), "colors": cols},
                {"t": nframes - 1 - hold, "positions": transformed.flatten().tolist(), "colors": cols},
                {"t": nframes - 1, "positions": transformed.flatten().tolist(), "colors": cols},
            ]),
        track=[Keyframe(0, [0, 0, 0])], layer="lattice")

    objects: list[SceneObject] = [lattice]

    # basis vectors: columns of I morphing to columns of M
    eye = np.eye(3) * S
    cols_M = (M.T * S)  # rows are transformed basis vectors e_i -> M e_i
    origin = np.zeros(3)
    for i in range(3):
        start_arrow = _arrow_points(origin, eye[i])
        end_arrow = _arrow_points(origin, cols_M[i])
        objects.append(SceneObject(
            id=f"basis_{i}",
            geometry=LineGeometry(color=_AXIS_COLORS[i], width=4.0, frames=[
                {"t": 0, "points": start_arrow},
                {"t": nframes - 1 - hold, "points": end_arrow},
                {"t": nframes - 1, "points": end_arrow}]),
            track=[Keyframe(0, [0, 0, 0])], layer="basis"))

    return Scene(
        title=f"Linear transform — {name} (det = {det:.2f})",
        fps=30, duration_frames=nframes, objects=objects,
        layers=[Layer("lattice", "Space (lattice)", "#9bd1ff"),
                Layer("basis", "Basis vectors", "#ff5b5b")],
        events=[{"t": 0, "label": "identity"},
                {"t": nframes - 1 - hold, "label": f"{name}: det = {det:.2f}"}],
        source="etu:linear_transform")
