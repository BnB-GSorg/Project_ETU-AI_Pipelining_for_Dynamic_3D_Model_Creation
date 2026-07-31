"""Template: vector_field — a 3D field of arrows.

ETU intent: vector fields are usually drawn flat on a slide, which hides the
spatial structure of rotation, sources, and saddles. Here the field fills 3D
space with arrows you can orbit, colored by magnitude.

params:
    field   : "rotation" | "source" | "saddle" | "shear" | "spiral"  (default "rotation")
    density : arrows per axis (density^3 arrows total)                 (default 5)
    scale   : arrow length scale                                       (default 0.45)
    extent  : half-width of the cube of sample points                  (default 2.0)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.colormap import viridis_like
from mmi.formats.mmi_scene import Keyframe, Layer, LineGeometry, Scene, SceneObject

_FIELDS = {
    "rotation": lambda x, y, z: np.array([-y, x, 0.0]),         # curl about z
    "source": lambda x, y, z: np.array([x, y, z]),             # radial outward
    "saddle": lambda x, y, z: np.array([x, -y, 0.0]),
    "shear": lambda x, y, z: np.array([y, 0.0, 0.0]),
    "spiral": lambda x, y, z: np.array([-y, x, 0.35]),         # rotation + rise
}


def _arrow_points(base: np.ndarray, vec: np.ndarray) -> list[float]:
    """A connected polyline that draws an arrow: base -> tip -> headL -> tip -> headR."""
    tip = base + vec
    n = np.linalg.norm(vec)
    if n < 1e-6:
        return (base.tolist() + tip.tolist())
    d = vec / n
    # pick a perpendicular for the arrowhead
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    p1 = np.cross(d, ref); p1 /= (np.linalg.norm(p1) + 1e-9)
    h = 0.28 * n
    headL = tip - d * h + p1 * h * 0.6
    headR = tip - d * h - p1 * h * 0.6
    pts = [base, tip, headL, tip, headR]
    return np.concatenate(pts).tolist()


def build(params: dict) -> Scene:
    field = params.get("field", "rotation")
    density = int(params.get("density", 5))
    scale = float(params.get("scale", 0.45))
    extent = float(params.get("extent", 2.0))
    F = _FIELDS.get(field, _FIELDS["rotation"])

    coords = np.linspace(-extent, extent, density)
    samples = [(x, y, z) for x in coords for y in coords for z in coords]
    vecs = [F(x, y, z) for (x, y, z) in samples]
    mags = np.array([np.linalg.norm(v) for v in vecs])
    mnorm = mags / (mags.max() + 1e-9)
    cols = viridis_like(mnorm)

    objects: list[SceneObject] = []
    for i, ((x, y, z), v) in enumerate(zip(samples, vecs)):
        base = np.array([x, y, z]) / extent * 2.6        # fit into scene
        vec = np.array(v) * scale
        c = "#%02x%02x%02x" % tuple(int(255 * t) for t in cols[i])
        objects.append(SceneObject(
            id=f"arrow_{i:03d}",
            geometry=LineGeometry(color=c, width=2.0, points=_arrow_points(base, vec)),
            track=[Keyframe(0, [0, 0, 0])], layer="field"))

    return Scene(
        title=f"3D vector field — {field}",
        fps=30, duration_frames=2, objects=objects,
        layers=[Layer("field", "Vectors (by magnitude)", "#37c98a")],
        events=[{"t": 0, "label": f"{field} field ({density}³ arrows)"}],
        source="etu:vector_field")
