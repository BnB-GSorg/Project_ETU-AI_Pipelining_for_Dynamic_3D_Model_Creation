"""Change-driven frame sampling — pick the timepoints that actually *change*.

Uniformly cutting N frames wastes budget on static stretches and can miss the
instant a process changes. Instead we measure how much the picture changes from
frame to frame and sample so that samples are **dense where change is fast and
sparse where the scene is still** — i.e. equal *amounts of change* between
samples, not equal time. Endpoints are always kept (start/end state).

This captures only *visual* change (cheap, no model call). Which of those changes
is *significant to the process* is left to the vision model downstream (it labels
states / writes the summary); this step just makes sure the model is shown the
frames where something happens.

`pick_indices` is pure (operates on a precomputed change signal) so it is unit
-testable without decoding images.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def pick_indices(change: np.ndarray, k: int) -> list[int]:
    """Choose ~k frame indices spaced by equal cumulative change.

    `change[i]` = visual change from frame i-1 to i (change[0] = 0). Returns a
    sorted list of distinct indices, always including the first and last frame.
    In flat regions the indices collapse (we don't waste samples on a still
    scene), so the result may be shorter than k — that is the point.
    """
    n = len(change)
    if n == 0:
        return []
    if n <= k or k <= 2:
        return list(range(n)) if n <= k else [0, n - 1]

    cum = np.cumsum(np.maximum(change, 0.0))
    total = float(cum[-1])
    if total <= 1e-9:                       # nothing moves -> fall back to uniform
        return [round(i * (n - 1) / (k - 1)) for i in range(k)]

    picks = {0, n - 1}
    for t in np.linspace(0.0, total, k):     # equal-change targets
        picks.add(int(np.searchsorted(cum, t, side="left")))
    return sorted(min(i, n - 1) for i in picks)


def _gray(path: Path, size: int = 96) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert("L").resize((size, size)), dtype=np.float32)


def change_signal(frames: list[Path]) -> np.ndarray:
    """Mean absolute frame-to-frame difference on small grayscale thumbnails."""
    grays = [_gray(p) for p in frames]
    sig = np.zeros(len(frames), dtype=np.float32)
    for i in range(1, len(frames)):
        sig[i] = float(np.mean(np.abs(grays[i] - grays[i - 1])))
    return sig


def select_by_change(frames: list[Path], k: int) -> list[Path]:
    """Pick up to k frames, weighted toward where the animation changes fast."""
    if len(frames) <= k:
        return frames
    idxs = pick_indices(change_signal(frames), k)
    return [frames[i] for i in idxs]
