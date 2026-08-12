"""Template: graph_surface — z = f(x, y) lifted from a flat heatmap.

ETU intent: a 2D heatmap of a function (what you'd draw on a slide) *is* a 3D
landscape. The scene morphs from the flat colored plane up into the surface, so
the viewer sees the hidden third dimension emerge.

params:
    func   : "saddle" | "gaussian" | "ripple" | "monkey"  (default "ripple")
    extent : half-width of the x/y domain                  (default 3.0)
    n      : grid resolution per axis                       (default 36)
    height : vertical exaggeration                          (default 1.6)
    frames : timeline length                                (default 80)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.colormap import viridis_like
from mmi.formats.mmi_scene import Keyframe, Layer, Scene, SceneObject, SurfaceGeometry

_FUNCS = {
    "saddle": lambda X, Y: X**2 - Y**2,
    "gaussian": lambda X, Y: np.exp(-(X**2 + Y**2)),
    "ripple": lambda X, Y: np.sinc(np.sqrt(X**2 + Y**2) / np.pi),
    "monkey": lambda X, Y: X**3 - 3 * X * Y**2,
}


def build(params: dict) -> Scene:
    func = params.get("func", "ripple")
    extent = float(params.get("extent", 3.0))
    n = int(params.get("n", 36))
    height = float(params.get("height", 1.6))
    nframes = int(params.get("frames", 80))
    f = _FUNCS.get(func, _FUNCS["ripple"])

    xs = np.linspace(-extent, extent, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    Z = f(X, Y)
    Z = Z / (np.abs(Z).max() + 1e-9) * height        # normalize height
    Zc = (Z - Z.min()) / (np.ptp(Z) + 1e-9)          # 0..1 for colormap
    colors = viridis_like(Zc.flatten())

    sx = X.flatten() / extent * 3.0                  # scene-space x,z in ~[-3,3]
    sz = Y.flatten() / extent * 3.0

    def grid_positions(zscale: float) -> list[float]:
        P = np.stack([sx, Z.flatten() * zscale, sz], axis=-1)
        return P.flatten().tolist()

    # morph: flat plane (z=0) -> full surface. Viewer interpolates -> smooth rise.
    hold = max(1, nframes // 5)
    frames = [
        {"t": 0, "positions": grid_positions(0.0), "colors": colors.flatten().tolist()},
        {"t": nframes - 1 - hold, "positions": grid_positions(1.0), "colors": colors.flatten().tolist()},
        {"t": nframes - 1, "positions": grid_positions(1.0), "colors": colors.flatten().tolist()},
    ]

    surf = SurfaceGeometry(rows=n, cols=n, wireframe=True, opacity=0.97, frames=frames)
    obj = SceneObject(id="surface", geometry=surf, track=[Keyframe(0, [0, 0, 0])], layer="surface")

    return Scene(
        title=f"z = f(x,y) — {func} (2D heatmap → 3D surface)",
        fps=30,
        duration_frames=nframes,
        objects=[obj],
        layers=[Layer("surface", "Surface", "#37c98a")],
        events=[{"t": 0, "label": "flat heatmap"}, {"t": nframes - 1 - hold, "label": "lifted to 3D surface"}],
        source="etu:graph_surface",
    )
