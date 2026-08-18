"""mmi-git v0.3 — a scene stored the way git stores a repository.

    base      the initial model: every part's geometry, as it starts
    commits   one per changed frame: a 4x4 delta per part ("the gits")
    keyframes periodic absolute snapshots, so seeking never replays far
    final     the last frame's poses, so the end state is readable directly

Storing deltas instead of per-frame snapshots is what makes the format small:
a frame costs 16 floats per part instead of a copy of its geometry.

Why poses and not raw vertices (this is the v0.2 change): v0.2 multiplied point
arrays directly, which silently threw away rotation, scale and opacity — an
animated scene compiled to zero commits. v0.3 commits carry the whole pose, so
lite -> git -> lite is lossless.

v0.2 files still load; their keyframes are regenerated because v0.2 stored
transformed points there while v0.3 stores poses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from etu.formats.scene import IDENTITY_QUAT, UNIT_SCALE, geometry_from_dict

FORMAT = "mmi-git"
VERSION = "0.3"
READABLE = ("0.1", "0.2", "0.3")

SNAPSHOT_INTERVAL = 30


# ── Matrix helpers ──────────────────────────────────────────────────────


def identity() -> list[float]:
    return np.eye(4).flatten().tolist()


def compose(position, quaternion, scale) -> np.ndarray:
    """Build the 4x4 for a pose, as T * R * S."""
    x, y, z, w = quaternion
    rot = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )
    m = np.eye(4)
    m[:3, :3] = rot * np.array(scale)  # scale columns, i.e. R @ diag(scale)
    m[:3, 3] = position
    return m


def decompose(m: np.ndarray) -> dict[str, Any]:
    """Split a 4x4 back into position, quaternion and scale."""
    position = m[:3, 3].tolist()
    basis = m[:3, :3]
    scale = np.linalg.norm(basis, axis=0)
    scale = np.where(scale < 1e-12, 1.0, scale)
    if np.linalg.det(basis) < 0:  # mirrored: fold the flip into the first axis
        scale[0] = -scale[0]
    return {
        "position": position,
        "quaternion": _quat_from_matrix(basis / scale),
        "scale": scale.tolist(),
    }


def _quat_from_matrix(r: np.ndarray) -> list[float]:
    """Rotation matrix to [x, y, z, w], via the largest-diagonal branch."""
    trace = r[0, 0] + r[1, 1] + r[2, 2]
    if trace > 0:
        s = np.sqrt(trace + 1.0) * 2
        q = [
            (r[2, 1] - r[1, 2]) / s,
            (r[0, 2] - r[2, 0]) / s,
            (r[1, 0] - r[0, 1]) / s,
            0.25 * s,
        ]
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
        q = [
            0.25 * s,
            (r[0, 1] + r[1, 0]) / s,
            (r[0, 2] + r[2, 0]) / s,
            (r[2, 1] - r[1, 2]) / s,
        ]
    elif r[1, 1] > r[2, 2]:
        s = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
        q = [
            (r[0, 1] + r[1, 0]) / s,
            0.25 * s,
            (r[1, 2] + r[2, 1]) / s,
            (r[0, 2] - r[2, 0]) / s,
        ]
    else:
        s = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
        q = [
            (r[0, 2] + r[2, 0]) / s,
            (r[1, 2] + r[2, 1]) / s,
            0.25 * s,
            (r[1, 0] - r[0, 1]) / s,
        ]
    n = float(np.linalg.norm(q))
    return (np.array(q) / n).tolist() if n else list(IDENTITY_QUAT)


def default_pose() -> dict[str, Any]:
    return {
        "position": [0.0, 0.0, 0.0],
        "quaternion": list(IDENTITY_QUAT),
        "scale": list(UNIT_SCALE),
        "opacity": 1.0,
    }


# ── Pieces ──────────────────────────────────────────────────────────────


@dataclass
class Part:
    """One movable piece of the model: a geometry plus its identity."""

    id: str
    label: str = ""
    geometry: Any = None
    layer: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label or self.id,
            "layer": self.layer,
            "geometry": self.geometry.to_dict() if self.geometry else None,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Part:
        geom = d.get("geometry")
        return Part(
            id=str(d["id"]),
            label=str(d.get("label", d["id"])),
            geometry=geometry_from_dict(geom) if geom else None,
            layer=str(d.get("layer", "default")),
        )


@dataclass
class Commit:
    """A frame's change: a 4x4 delta per part, plus any opacity change.

    Opacity rides alongside rather than inside the matrix — a 4x4 has nowhere
    to put it, and dropping it is what made the old converter lose fades.
    """

    t: int
    transforms: dict[str, list[float]] = field(default_factory=dict)
    opacity: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"t": self.t, "transforms": self.transforms}
        if self.opacity:
            d["opacity"] = self.opacity
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Commit:
        return Commit(
            t=int(d["t"]),
            transforms={
                k: [float(x) for x in v] for k, v in d.get("transforms", {}).items()
            },
            opacity={k: float(v) for k, v in d.get("opacity", {}).items()},
        )

    def matrix_for(self, part_id: str) -> np.ndarray:
        flat = self.transforms.get(part_id)
        return np.eye(4) if flat is None else np.array(flat, dtype=float).reshape(4, 4)


@dataclass
class Snapshot:
    """Absolute poses at frame `t` — a keyframe, or the final state."""

    t: int
    poses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "poses": self.poses}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Snapshot:
        return Snapshot(t=int(d["t"]), poses=dict(d.get("poses", {})))


# ── Scene ───────────────────────────────────────────────────────────────


@dataclass
class GitScene:
    """A scene as initial model + commit chain + final model."""

    title: str
    fps: int = 30
    duration_frames: int = 1
    parts: list[Part] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    keyframes: list[Snapshot] = field(default_factory=list)
    final: Snapshot | None = None
    layers: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    source: str = "etu"

    # ── serialization ───────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "version": VERSION,
            "meta": {
                "title": self.title,
                "fps": self.fps,
                "duration_frames": self.duration_frames,
                "source": self.source,
                "coordinate_system": "right-handed-y-up",
                "events": self.events,
            },
            "base": {"parts": [p.to_dict() for p in self.parts]},
            "commits": [c.to_dict() for c in self.commits],
            "keyframes": [k.to_dict() for k in self.keyframes],
            "final": self.final.to_dict() if self.final else None,
            "layers": self.layers,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> GitScene:
        version = str(d.get("version", VERSION))
        if version not in READABLE:
            raise ValueError(
                f"unsupported mmi-git version {version!r} (readable: {', '.join(READABLE)})"
            )

        meta = d.get("meta", {})
        base = d.get("base", {})
        scene = GitScene(
            title=str(meta.get("title", "untitled")),
            fps=int(meta.get("fps", 30)),
            duration_frames=int(meta.get("duration_frames", 1)),
            commits=[Commit.from_dict(c) for c in d.get("commits", [])],
            layers=list(d.get("layers", [])),
            events=list(meta.get("events", [])),
            source=str(meta.get("source", "etu")),
        )

        if "parts" in base:
            scene.parts = [Part.from_dict(p) for p in base["parts"]]
            scene.keyframes = [Snapshot.from_dict(k) for k in d.get("keyframes", [])]
            if d.get("final"):
                scene.final = Snapshot.from_dict(d["final"])
        else:
            scene.parts = _parts_from_v02(base, d.get("parts", []))

        # v0.2 keyframes held transformed points, not poses; rebuild them.
        if not scene.keyframes:
            scene.generate_keyframes()
        if scene.final is None:
            scene.final = Snapshot(
                t=scene.duration_frames - 1,
                poses=scene.decode(scene.duration_frames - 1),
            )
        return scene

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    @staticmethod
    def load(path: str | Path) -> GitScene:
        return GitScene.from_dict(json.loads(Path(path).read_text()))

    # ── playback ────────────────────────────────────────────────────────

    def decode(self, t: int) -> dict[str, dict[str, Any]]:
        """Poses at frame `t`, reached from whichever snapshot is closer.

        Seeking backwards walks down from a later snapshot by inverting the
        commits in between, so scrubbing right-to-left costs the same as
        left-to-right instead of restarting from frame 0.
        """
        t = max(0, min(int(t), self.duration_frames - 1))
        before, after = self._surrounding_snapshots(t)

        rewind_is_closer = after is not None and (
            before is None or (after.t - t) < (t - before.t)
        )
        if rewind_is_closer:
            return self._rewind_to(after, t)
        return self._replay_to(before, t)

    def _surrounding_snapshots(self, t: int) -> tuple[Snapshot | None, Snapshot | None]:
        before = after = None
        for snap in self._all_snapshots():
            if snap.t <= t and (before is None or snap.t > before.t):
                before = snap
            if snap.t >= t and (after is None or snap.t < after.t):
                after = snap
        return before, after

    def _all_snapshots(self) -> list[Snapshot]:
        snaps = list(self.keyframes)
        if self.final:
            snaps.append(self.final)
        return snaps

    def _replay_to(self, start: Snapshot | None, t: int) -> dict[str, dict[str, Any]]:
        poses = (
            _copy_poses(start.poses)
            if start
            else {p.id: default_pose() for p in self.parts}
        )
        start_t = start.t if start else -1
        for commit in sorted(self.commits, key=lambda c: c.t):
            if commit.t <= start_t:
                continue
            if commit.t > t:
                break
            _apply(poses, commit, forward=True)
        return poses

    def _rewind_to(self, start: Snapshot, t: int) -> dict[str, dict[str, Any]]:
        poses = _copy_poses(start.poses)
        for commit in sorted(self.commits, key=lambda c: c.t, reverse=True):
            if commit.t > start.t:
                continue
            if commit.t <= t:
                break
            _apply(poses, commit, forward=False)
        return poses

    def generate_keyframes(self, interval: int = SNAPSHOT_INTERVAL) -> list[Snapshot]:
        """Lay down periodic absolute snapshots so seeking stays cheap."""
        self.keyframes = []  # cleared first so replay starts from the base
        snaps = []
        for t in range(0, self.duration_frames, max(1, interval)):
            snaps.append(Snapshot(t=t, poses=self._replay_to(None, t)))
        self.keyframes = snaps
        return snaps

    # ── checks ──────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.duration_frames < 1:
            problems.append("duration_frames must be >= 1")
        if self.fps < 1:
            problems.append("fps must be >= 1")
        if not self.parts:
            problems.append("scene has no parts")

        known = {p.id for p in self.parts}
        if len(known) != len(self.parts):
            problems.append("duplicate part ids in base")

        seen_t: set[int] = set()
        for c in self.commits:
            if not 0 <= c.t < self.duration_frames:
                problems.append(f"commit t={c.t} outside 0..{self.duration_frames - 1}")
            if c.t in seen_t:
                problems.append(f"duplicate commit at t={c.t}")
            seen_t.add(c.t)
            for pid, flat in c.transforms.items():
                if pid not in known:
                    problems.append(f"commit t={c.t} targets unknown part {pid!r}")
                if len(flat) != 16:
                    problems.append(
                        f"commit t={c.t} part {pid!r}: expected 16 matrix values, got {len(flat)}"
                    )

        for snap in self.keyframes:
            if not 0 <= snap.t < self.duration_frames:
                problems.append(
                    f"keyframe t={snap.t} outside 0..{self.duration_frames - 1}"
                )
            for pid in snap.poses:
                if pid not in known:
                    problems.append(
                        f"keyframe t={snap.t} references unknown part {pid!r}"
                    )

        if self.final is None:
            problems.append("missing final model")
        elif self.final.t != self.duration_frames - 1:
            problems.append(
                f"final model at t={self.final.t}, expected {self.duration_frames - 1}"
            )

        return problems

    @property
    def commit_count(self) -> int:
        return len(self.commits)


# ── internals ───────────────────────────────────────────────────────────


def _apply(poses: dict[str, dict[str, Any]], commit: Commit, forward: bool) -> None:
    for pid, flat in commit.transforms.items():
        pose = poses.get(pid)
        if pose is None:
            continue
        delta = np.array(flat, dtype=float).reshape(4, 4)
        if not forward:
            delta = np.linalg.inv(delta)
        current = compose(pose["position"], pose["quaternion"], pose["scale"])
        pose.update(decompose(current @ delta))

    for pid, value in commit.opacity.items():
        # Rewinding restores what the previous commit left, which the
        # snapshot we started from already accounts for.
        if pid in poses and forward:
            poses[pid]["opacity"] = value


def _copy_poses(poses: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        pid: {k: (list(v) if isinstance(v, list) else v) for k, v in pose.items()}
        for pid, pose in poses.items()
    }


def _parts_from_v02(base: dict[str, Any], parts: list[dict[str, Any]]) -> list[Part]:
    """Read a v0.1/v0.2 base: one shared point array carved up by index."""
    from etu.formats.scene import PointCloud

    points = [float(v) for v in base.get("points", [])]
    colors = base.get("colors")
    out: list[Part] = []
    for spec in parts:
        idx = [int(i) for i in spec.get("point_indices", [])]
        out.append(
            Part(
                id=str(spec["id"]),
                label=str(spec.get("label", spec["id"])),
                geometry=PointCloud(
                    points=[v for i in idx for v in points[i * 3 : i * 3 + 3]],
                    colors=(
                        [float(colors[j]) for i in idx for j in range(i * 3, i * 3 + 3)]
                        if colors
                        else None
                    ),
                ),
                layer=str(spec.get("id")),
            )
        )
    return out
