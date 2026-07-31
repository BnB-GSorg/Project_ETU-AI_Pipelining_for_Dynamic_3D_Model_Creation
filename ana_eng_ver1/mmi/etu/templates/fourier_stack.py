"""Template: fourier_stack — a square wave decomposed along a new axis.

ETU intent: a flat plot of a square wave hides that it is a *sum of sine
harmonics*. We spread the harmonics along a new depth axis (z), draw a running
sum that morphs as more terms are added, and show the ideal square wave as the
target the sum converges to. The hidden structure (the decomposition) becomes a
literal third dimension.

params:
    harmonics : number of odd harmonics to stack   (default 8)
    samples   : x-resolution per curve             (default 220)
    spacing   : depth gap between harmonic layers   (default 0.9)
    yscale    : vertical amplitude scale            (default 1.3)
    frames    : timeline length                     (default 90)
"""

from __future__ import annotations

import numpy as np

from mmi.etu.colormap import viridis_like
from mmi.formats.mmi_scene import Keyframe, Layer, LineGeometry, Scene, SceneObject


def _curve(sx: np.ndarray, y: np.ndarray, z: float) -> list[float]:
    return np.stack([sx, y, np.full_like(sx, z)], axis=-1).flatten().tolist()


def build(params: dict) -> Scene:
    K = int(params.get("harmonics", 8))
    m = int(params.get("samples", 220))
    spacing = float(params.get("spacing", 0.9))
    yscale = float(params.get("yscale", 1.3))
    nframes = int(params.get("frames", 90))

    x = np.linspace(0, 1, m, endpoint=False)
    sx = (x - 0.5) * 6.0                              # scene x in [-3, 3]
    two_pi = 2 * np.pi

    terms = [(4 / np.pi) * (1 / (2 * k - 1)) * np.sin(two_pi * (2 * k - 1) * x) for k in range(1, K + 1)]
    hcolors = viridis_like(np.linspace(0, 1, K))

    objects: list[SceneObject] = []

    # 1) individual harmonics, receding along -z
    for k, term in enumerate(terms):
        z = -k * spacing
        c = "#%02x%02x%02x" % tuple(int(255 * v) for v in hcolors[k])
        objects.append(
            SceneObject(
                id=f"harmonic_{2*k+1}",
                geometry=LineGeometry(color=c, width=2.0, points=_curve(sx, term * yscale, z)),
                track=[Keyframe(0, [0, 0, 0])],
                layer="harmonics",
            )
        )

    # 2) running sum that morphs as terms are added (convergence)
    front_z = 1.4
    cum = np.cumsum(terms, axis=0)                    # cum[k] = sum of first k+1 terms
    hold = max(1, nframes // 6)
    span = nframes - 1 - hold
    sum_frames = []
    for k in range(K):
        t = 0 if K == 1 else round(k / (K - 1) * span)
        sum_frames.append({"t": t, "points": _curve(sx, cum[k] * yscale, front_z)})
    sum_frames.append({"t": nframes - 1, "points": _curve(sx, cum[-1] * yscale, front_z)})
    objects.append(
        SceneObject(
            id="running_sum",
            geometry=LineGeometry(color="#ffffff", width=4.0, frames=sum_frames),
            track=[Keyframe(0, [0, 0, 0])],
            layer="sum",
        )
    )

    # 3) ideal square wave target (the limit), front-most
    square = np.sign(np.sin(two_pi * x)) * (4 / np.pi) * 0.785  # ~unit amplitude
    objects.append(
        SceneObject(
            id="target_square",
            geometry=LineGeometry(color="#ff6b6b", width=2.5, points=_curve(sx, square * yscale, front_z + spacing)),
            track=[Keyframe(0, [0, 0, 0])],
            layer="target",
        )
    )

    events = [
        {"t": (0 if K == 1 else round(k / (K - 1) * span)), "label": f"sum of {k+1} harmonic{'s' if k else ''}"}
        for k in range(K)
    ]

    return Scene(
        title="Square wave = sum of sine harmonics (decomposed along depth)",
        fps=30,
        duration_frames=nframes,
        objects=objects,
        layers=[
            Layer("harmonics", "Harmonics (stacked)", "#37c98a"),
            Layer("sum", "Running sum", "#ffffff"),
            Layer("target", "Ideal square wave", "#ff6b6b"),
        ],
        events=events,
        source="etu:fourier_stack",
    )
