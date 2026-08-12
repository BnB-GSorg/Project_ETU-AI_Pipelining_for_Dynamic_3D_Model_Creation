"""Template: taylor_series — polynomial approximation, stacked by degree.

ETU intent: a flat plot of "f(x) and its Taylor approximations" hides the
*successive* structure. We stack each added term along a depth axis, draw a
running approximation that morphs as the degree grows, and show the target
function it converges to.

params:
    func   : "sin" | "cos" | "exp" | "geometric" | "log1p"   (default "sin")
    terms  : number of series terms to add                    (default 6)
    spacing: depth gap between term layers                     (default 0.9)
    yscale : vertical amplitude scale                          (default 1.3)
    frames : timeline length                                  (default 90)
"""

from __future__ import annotations

import math

import numpy as np

from mmi.etu.colormap import viridis_like
from mmi.formats.mmi_scene import Keyframe, Layer, LineGeometry, Scene, SceneObject

# (domain, target fn, term_k fn) per function. term_k returns the k-th series term (k>=0).
_SPECS = {
    "sin": ((-2 * np.pi, 2 * np.pi), np.sin,
            lambda x, k: (-1) ** k * x ** (2 * k + 1) / math.factorial(2 * k + 1)),
    "cos": ((-2 * np.pi, 2 * np.pi), np.cos,
            lambda x, k: (-1) ** k * x ** (2 * k) / math.factorial(2 * k)),
    "exp": ((-2.0, 2.5), np.exp,
            lambda x, k: x ** k / math.factorial(k)),
    "geometric": ((-0.8, 0.8), lambda x: 1.0 / (1.0 - x),
                  lambda x, k: x ** k),
    "log1p": ((-0.8, 2.5), np.log1p,
              lambda x, k: (0.0 if k == 0 else (-1) ** (k + 1) * x ** k / k)),
}


def _curve(sx, y, z):
    return np.stack([sx, y, np.full_like(sx, z)], axis=-1).flatten().tolist()


def build(params: dict) -> Scene:
    func = params.get("func", "sin")
    T = int(params.get("terms", 6))
    spacing = float(params.get("spacing", 0.9))
    yscale = float(params.get("yscale", 1.3))
    nframes = int(params.get("frames", 90))
    (lo, hi), target_fn, term_fn = _SPECS.get(func, _SPECS["sin"])

    x = np.linspace(lo, hi, 240)
    sx = (x - (lo + hi) / 2) / (hi - lo) * 6.0          # scene x in [-3, 3]
    target = np.asarray(target_fn(x), dtype=float)
    norm = max(float(np.abs(target).max()), 1e-9)

    terms = [np.asarray(term_fn(x, k), dtype=float) for k in range(T)]
    cum = np.cumsum(terms, axis=0)
    hcolors = viridis_like(np.linspace(0, 1, T))

    objects: list[SceneObject] = []
    for k, term in enumerate(terms):
        c = "#%02x%02x%02x" % tuple(int(255 * v) for v in hcolors[k])
        objects.append(SceneObject(
            id=f"term_{k}",
            geometry=LineGeometry(color=c, width=2.0, points=_curve(sx, term / norm * yscale, -k * spacing)),
            track=[Keyframe(0, [0, 0, 0])], layer="terms"))

    front_z = 1.4
    hold = max(1, nframes // 6)
    span = nframes - 1 - hold
    sum_frames = [{"t": (0 if T == 1 else round(k / (T - 1) * span)),
                   "points": _curve(sx, np.clip(cum[k] / norm, -2, 2) * yscale, front_z)} for k in range(T)]
    sum_frames.append({"t": nframes - 1, "points": _curve(sx, np.clip(cum[-1] / norm, -2, 2) * yscale, front_z)})
    objects.append(SceneObject(
        id="approximation",
        geometry=LineGeometry(color="#ffffff", width=4.0, frames=sum_frames),
        track=[Keyframe(0, [0, 0, 0])], layer="approx"))

    objects.append(SceneObject(
        id="target",
        geometry=LineGeometry(color="#ff6b6b", width=2.5, points=_curve(sx, target / norm * yscale, front_z + spacing)),
        track=[Keyframe(0, [0, 0, 0])], layer="target"))

    events = [{"t": (0 if T == 1 else round(k / (T - 1) * span)), "label": f"{k+1} term(s)"} for k in range(T)]
    return Scene(
        title=f"Taylor series of {func} (approximation stacked by degree)",
        fps=30, duration_frames=nframes, objects=objects,
        layers=[Layer("terms", "Series terms", "#37c98a"),
                Layer("approx", "Running approximation", "#ffffff"),
                Layer("target", f"Target: {func}", "#ff6b6b")],
        events=events, source="etu:taylor_series")
