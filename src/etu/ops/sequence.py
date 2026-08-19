"""Run a whole sequence of operations, collecting the commits as it goes.

Each move is spread over `frames_per_move` commits so playback is a smooth
turn rather than a jump. Every commit carries the move that produced it in
its `op` field, so "which gits belong to move 7" is still answerable — and
`frames_per_move=1` gives literally one commit per move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from etu.formats.git import Commit, Snapshot
from etu.model import Model
from etu.ops.executor import apply_move, snap

FRAMES_PER_MOVE = 6
HOLD_FRAMES = 1  # a beat between moves, so each one reads as a separate step


@dataclass
class Execution:
    """Everything a run produced: where it started, ended, and every step."""

    initial: Snapshot
    final: Snapshot
    commits: list[Commit] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    duration_frames: int = 1
    model: Model | None = None


def run(
    model: Model,
    moves: list[str],
    frames_per_move: int = FRAMES_PER_MOVE,
    hold_frames: int = HOLD_FRAMES,
) -> Execution:
    """Apply `moves` to a copy of `model`, recording a commit per frame."""
    working = model.copy()
    working.ensure_poses()
    initial = working.snapshot(0)

    commits: list[Commit] = []
    events: list[dict[str, Any]] = []
    frame = 0
    steps = max(1, frames_per_move)

    for number, move in enumerate(moves, start=1):
        events.append({"t": frame, "label": f"{number}. {move}"})
        for _ in range(steps):
            frame += 1
            commits.append(apply_move(working, move, t=frame, fraction=1.0 / steps))
        snap(working)
        frame += max(0, hold_frames)

    duration = frame + 1
    return Execution(
        initial=initial,
        final=working.snapshot(duration - 1),
        commits=commits,
        events=events,
        duration_frames=duration,
        model=working,
    )
