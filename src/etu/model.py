"""A model: the parts that make it up, and where each one currently sits.

This is the thing that flows through the pipeline — the knowledge base builds
one, operations mutate it, and the compiler freezes it into a file. It is
deliberately the same shape as mmi-git's `base` (parts) plus a `Snapshot`
(poses), so handing it to the compiler needs no translation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from etu.formats.git import Part, Snapshot, default_pose


@dataclass
class Model:
    """Parts plus their current poses."""

    concept: str = ""
    parts: list[Part] = field(default_factory=list)
    poses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def snapshot(self, t: int) -> Snapshot:
        """Freeze the current poses as a snapshot at frame `t`."""
        return Snapshot(t=t, poses=_copy(self.poses))

    def copy(self) -> Model:
        """A deep-enough copy that mutating one model cannot disturb the other."""
        return Model(
            concept=self.concept, parts=list(self.parts), poses=_copy(self.poses)
        )

    def part_ids(self) -> list[str]:
        return [p.id for p in self.parts]

    def ensure_poses(self) -> None:
        """Give any part without a pose the identity pose."""
        for part in self.parts:
            self.poses.setdefault(part.id, default_pose())


def _copy(poses: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        pid: {k: (list(v) if isinstance(v, list) else v) for k, v in pose.items()}
        for pid, pose in poses.items()
    }
