"""Tiny dependency-free colormaps for the math templates."""

from __future__ import annotations

import numpy as np


def coolwarm(t: np.ndarray) -> np.ndarray:
    """Diverging blue->white->red map. ``t`` in [0,1], returns (N,3) in 0..1."""
    t = np.clip(t, 0, 1)
    lo = np.array([0.23, 0.30, 0.75])
    mid = np.array([0.95, 0.95, 0.95])
    hi = np.array([0.71, 0.02, 0.15])
    t2 = (t[:, None] - 0.5) * 2
    below = lo + (mid - lo) * (t[:, None] * 2)
    above = mid + (hi - mid) * t2
    return np.where(t[:, None] < 0.5, below, above)


def viridis_like(t: np.ndarray) -> np.ndarray:
    """Cheap perceptual-ish dark-blue -> green -> yellow map."""
    t = np.clip(t, 0, 1)
    stops = np.array([
        [0.27, 0.00, 0.33], [0.22, 0.33, 0.55], [0.13, 0.57, 0.55],
        [0.37, 0.79, 0.38], [0.99, 0.91, 0.14],
    ])
    x = t * (len(stops) - 1)
    i = np.clip(x.astype(int), 0, len(stops) - 2)
    f = (x - i)[:, None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorized HSV->RGB. h,s,v in [0,1], returns (N,3)."""
    h = (h % 1.0) * 6.0
    i = np.floor(h).astype(int)
    f = h - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)
