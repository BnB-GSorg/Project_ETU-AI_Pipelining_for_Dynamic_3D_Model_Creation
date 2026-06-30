"""Template: parametric_surface — a (u,v) surface lifted from its flat domain.

ETU intent: a parametric surface is taught as equations x(u,v), y(u,v), z(u,v)
over a flat parameter rectangle. Here the flat (u,v) domain morphs up into the
actual 3D shape, making the mapping tangible.

params:
    shape : "torus" | "sphere" | "helicoid" | "mobius"   (default "torus")
    n     : grid resolution per parameter                 (default 48)
    frames: timeline length                               (default 90)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.colormap import viridis_like
from mmi.formats.mmi_scene import Keyframe, Layer, Scene, SceneObject, SurfaceGeometry

TAU = 2 * np.pi


def _shape(name: str, U: np.ndarray, V: np.ndarray):
    if name == "sphere":
        x = np.sin(V) * np.cos(U); y = np.cos(V); z = np.sin(V) * np.sin(U)
        return 2.2 * x, 2.2 * y, 2.2 * z
    if name == "helicoid":
        x = V * np.cos(U); y = 0.5 * (U - TAU); z = V * np.sin(U)
        return 1.1 * x, 1.1 * y, 1.1 * z
    if name == "mobius":
        x = (1 + V / 2 * np.cos(U / 2)) * np.cos(U)
        y = V / 2 * np.sin(U / 2)
        z = (1 + V / 2 * np.cos(U / 2)) * np.sin(U)
        return 1.8 * x, 1.8 * y, 1.8 * z
    # torus
    R, r = 1.4, 0.55
    x = (R + r * np.cos(V)) * np.cos(U)
    y = r * np.sin(V)
    z = (R + r * np.cos(V)) * np.sin(U)
    return 1.4 * x, 1.4 * y, 1.4 * z


_RANGES = {
    "torus": (TAU, TAU), "sphere": (TAU, np.pi),
    "helicoid": (2 * TAU, None), "mobius": (TAU, None),
}


def build(params: dict) -> Scene:
    shape = params.get("shape", "torus")
    n = int(params.get("n", 48))
    nframes = int(params.get("frames", 90))

    u_max, v_max = _RANGES.get(shape, _RANGES["torus"])
    u = np.linspace(0, u_max, n)
    v = (np.linspace(0, v_max, n) if v_max is not None else np.linspace(-1, 1, n))
    U, V = np.meshgrid(u, v, indexing="ij")
    X, Y, Z = _shape(shape, U, V)

    # flat parameter domain, centered and scaled into the scene plane
    fu = (U - U.mean()) / (U.max() - U.min() + 1e-9) * 6.0
    fv = (V - V.mean()) / (V.max() - V.min() + 1e-9) * 6.0
    flat = np.stack([fu.flatten(), np.zeros(U.size), fv.flatten()], axis=-1)
    surf = np.stack([X.flatten(), Y.flatten(), Z.flatten()], axis=-1)
    colors = viridis_like((V.flatten() - V.min()) / (np.ptp(V) + 1e-9)).flatten().tolist()

    hold = max(1, nframes // 5)
    frames = [
        {"t": 0, "positions": flat.flatten().tolist(), "colors": colors},
        {"t": nframes - 1 - hold, "positions": surf.flatten().tolist(), "colors": colors},
        {"t": nframes - 1, "positions": surf.flatten().tolist(), "colors": colors},
    ]

    obj = SceneObject(
        id="surface",
        geometry=SurfaceGeometry(rows=n, cols=n, wireframe=False, opacity=1.0, frames=frames),
        track=[Keyframe(0, [0, 0, 0])], layer="surface")

    return Scene(
        title=f"Parametric surface — {shape} (flat (u,v) domain → 3D shape)",
        fps=30, duration_frames=nframes, objects=[obj],
        layers=[Layer("surface", f"{shape} surface", "#c05bd8")],
        events=[{"t": 0, "label": "flat (u,v) parameter domain"},
                {"t": nframes - 1 - hold, "label": f"mapped to 3D {shape}"}],
        source="etu:parametric_surface")
