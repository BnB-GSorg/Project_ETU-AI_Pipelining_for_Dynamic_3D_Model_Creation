"""A viridis-like colour ramp, so templates can colour by value without matplotlib."""

from __future__ import annotations

import numpy as np

# Six viridis anchors, dark blue to yellow. Enough to read as a smooth ramp
# once interpolated; the exact curve does not matter for comprehension.
_ANCHORS = np.array(
    [
        [0.267, 0.005, 0.329],
        [0.283, 0.141, 0.458],
        [0.254, 0.265, 0.530],
        [0.207, 0.372, 0.553],
        [0.128, 0.567, 0.551],
        [0.993, 0.906, 0.144],
    ]
)


def viridis_like(values) -> np.ndarray:
    """Map values in 0..1 to (N, 3) RGB in 0..1."""
    t = np.clip(np.asarray(values, dtype=float).ravel(), 0.0, 1.0)
    scaled = t * (len(_ANCHORS) - 1)
    low = np.floor(scaled).astype(int)
    high = np.minimum(low + 1, len(_ANCHORS) - 1)
    frac = (scaled - low)[:, None]
    return _ANCHORS[low] * (1 - frac) + _ANCHORS[high] * frac


def hex_of(rgb) -> str:
    """Format one RGB triple in 0..1 as #rrggbb."""
    r, g, b = (round(255 * float(c)) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def ramp_hex(n: int) -> list[str]:
    """`n` hex colours evenly spaced along the ramp."""
    if n <= 0:
        return []
    if n == 1:
        return [hex_of(viridis_like([0.5])[0])]
    return [hex_of(c) for c in viridis_like(np.linspace(0.0, 1.0, n))]


def hex_to_rgb01(value: str) -> list[float]:
    """Parse #rrggbb to RGB in 0..1, falling back to a neutral blue."""
    text = value.lstrip("#")
    if len(text) != 6:
        return [0.55, 0.70, 1.0]
    try:
        return [int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    except ValueError:
        return [0.55, 0.70, 1.0]
