"""Template: complex_surface — a complex function f(z) as a 3D landscape.

ETU intent: the flat "domain coloring" picture used to teach complex functions
(hue = arg f, brightness = |f|) hides that |f| is really a height field. This
scene shows the familiar flat colored disk, then morphs it up into the 3D
modulus landscape — poles become spires, zeros become pits.

params:
    func   : "z^2" | "z^3-1" | "1/z" | "(z^2-1)/(z^2+1)"  (default "z^3-1")
    extent : half-width of the complex domain               (default 1.6)
    n      : grid resolution                                 (default 44)
    height : vertical exaggeration                           (default 1.4)
    clip   : clamp |f| so poles don't shoot to infinity      (default 3.0)
    frames : timeline length                                 (default 90)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.colormap import hsv_to_rgb
from mmi.formats.mmi_scene import Keyframe, Layer, Scene, SceneObject, SurfaceGeometry

_FUNCS = {
    "z^2": lambda Z: Z**2,
    "z^3-1": lambda Z: Z**3 - 1,
    "1/z": lambda Z: 1.0 / (Z + 1e-6),
    "(z^2-1)/(z^2+1)": lambda Z: (Z**2 - 1) / (Z**2 + 1 + 1e-9),
}


def build(params: dict) -> Scene:
    func = params.get("func", "z^3-1")
    extent = float(params.get("extent", 1.6))
    n = int(params.get("n", 44))
    height = float(params.get("height", 1.4))
    clip = float(params.get("clip", 3.0))
    nframes = int(params.get("frames", 90))
    f = _FUNCS.get(func, _FUNCS["z^3-1"])

    xs = np.linspace(-extent, extent, n)
    RE, IM = np.meshgrid(xs, xs, indexing="ij")
    W = f(RE + 1j * IM)

    mag = np.abs(W)
    mag_c = np.clip(mag, 0, clip)
    Z = mag_c / (clip) * height                      # height field
    arg = np.angle(W)                                # -pi..pi
    hue = (arg / (2 * np.pi)) % 1.0
    val = 0.55 + 0.45 * (mag_c / clip)               # brighter where |f| larger
    colors = hsv_to_rgb(hue.flatten(), np.full(hue.size, 0.85), val.flatten())

    sx = RE.flatten() / extent * 3.0
    sz = IM.flatten() / extent * 3.0

    def positions(zscale: float) -> list[float]:
        return np.stack([sx, Z.flatten() * zscale, sz], axis=-1).flatten().tolist()

    hold = max(1, nframes // 5)
    cflat = colors.flatten().tolist()
    frames = [
        {"t": 0, "positions": positions(0.0), "colors": cflat},
        {"t": nframes - 1 - hold, "positions": positions(1.0), "colors": cflat},
        {"t": nframes - 1, "positions": positions(1.0), "colors": cflat},
    ]

    surf = SurfaceGeometry(rows=n, cols=n, wireframe=False, opacity=1.0, frames=frames)
    obj = SceneObject(id="modulus", geometry=surf, track=[Keyframe(0, [0, 0, 0])], layer="modulus")

    return Scene(
        title=f"f(z) = {func} — domain coloring → 3D |f| landscape",
        fps=30,
        duration_frames=nframes,
        objects=[obj],
        layers=[Layer("modulus", "|f(z)| surface", "#c05bd8")],
        events=[
            {"t": 0, "label": "flat domain coloring (hue = arg f)"},
            {"t": nframes - 1 - hold, "label": "height = |f(z)|: poles & zeros revealed"},
        ],
        source="etu:complex_surface",
    )
