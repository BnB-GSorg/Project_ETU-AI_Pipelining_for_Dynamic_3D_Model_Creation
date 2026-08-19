"""Apply one operation to a model and record what changed.

A move is a world-space rotation about an axis through the model's centre,
but a commit stores a *local* delta, because that is what mmi-git replays:
`M_new = M_current @ delta`. So the delta is read off after the fact —
`delta = inv(before) @ after` — which is the same rule the mmi-lite compiler
uses, and means both paths produce files that decode identically.
"""

from __future__ import annotations

import numpy as np

from etu.formats.git import Commit, compose, decompose
from etu.kb import rubiks
from etu.model import Model


def apply_move(model: Model, move: str, t: int = 0, fraction: float = 1.0) -> Commit:
    """Turn a layer and return the commit describing the turn.

    `fraction` turns only part of the way, which is how a move is animated
    over several frames — six commits of a sixth each look like one smooth
    90-degree turn, and still add up to exactly the same final state.
    """
    axis, _, degrees = rubiks.turn(move)
    world = rubiks.rotation(axis, degrees * fraction)

    transforms: dict[str, list[float]] = {}
    for pid in rubiks.layer_members(model, move):
        pose = model.poses[pid]
        before = compose(pose["position"], pose["quaternion"], pose["scale"])
        after = world @ before
        transforms[pid] = (np.linalg.inv(before) @ after).flatten().tolist()
        pose.update(decompose(after))

    return Commit(t=t, transforms=transforms, op=move)


def snap(model: Model) -> None:
    """Round poses back to the lattice, so float drift cannot accumulate.

    Called after each completed move: a cubie is always at integer coordinates
    between moves, so anything else is rounding error from the rotations.
    """
    for pose in model.poses.values():
        pose["position"] = [float(round(v)) for v in pose["position"]]
