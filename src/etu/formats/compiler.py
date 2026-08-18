"""Convert between mmi-lite and mmi-git, in both directions.

The old converter only went lite -> git and carried position and rotation, so
scale and opacity vanished and a scene whose objects only ever scaled compiled
to zero commits. Here a commit is emitted wherever any pose channel changes,
and git -> lite exists, so a compiled file can be opened back up.
"""

from __future__ import annotations

import numpy as np

from etu.formats.git import (
    Commit,
    GitScene,
    Part,
    Snapshot,
    compose,
    decompose,
    default_pose,
)
from etu.formats.scene import Keyframe, Layer, Scene, SceneObject, sample_track

TOLERANCE = 1e-9


def to_git(scene: Scene, snapshot_interval: int = 30) -> GitScene:
    """Compile an mmi-lite scene into mmi-git: base, commits, final."""
    parts = [
        Part(id=o.id, label=o.id, geometry=o.geometry, layer=o.layer)
        for o in scene.objects
    ]

    # Commit only where something moved. Every object's keyframe times are
    # candidates; frame 0 anchors the base pose.
    times = sorted({k.t for o in scene.objects for k in o.track} | {0})

    commits: list[Commit] = []
    previous = {o.id: default_pose() for o in scene.objects}

    for t in times:
        transforms: dict[str, list[float]] = {}
        opacity: dict[str, float] = {}

        for obj in scene.objects:
            current = sample_track(obj.track, t)
            before = previous[obj.id]

            if not _same_pose(before, current):
                m_before = compose(
                    before["position"], before["quaternion"], before["scale"]
                )
                m_current = compose(
                    current["position"], current["quaternion"], current["scale"]
                )
                delta = np.linalg.inv(m_before) @ m_current
                transforms[obj.id] = delta.flatten().tolist()

            if abs(current["opacity"] - before["opacity"]) > TOLERANCE:
                opacity[obj.id] = current["opacity"]

            previous[obj.id] = current

        if transforms or opacity:
            commits.append(Commit(t=t, transforms=transforms, opacity=opacity))

    git = GitScene(
        title=scene.title,
        fps=scene.fps,
        duration_frames=scene.duration_frames,
        parts=parts,
        commits=commits,
        layers=[layer.to_dict() for layer in scene.layers],
        events=list(scene.events),
        source=f"compiled:{scene.source}",
    )
    git.generate_keyframes(snapshot_interval)
    last = scene.duration_frames - 1
    git.final = Snapshot(t=last, poses=git.decode(last))
    return git


def to_lite(git: GitScene) -> Scene:
    """Decompile mmi-git back to mmi-lite by decoding each commit frame."""
    times = sorted({c.t for c in git.commits} | {0, git.duration_frames - 1})
    states = {t: git.decode(t) for t in times}

    objects: list[SceneObject] = []
    for part in git.parts:
        track = []
        for t in times:
            pose = states[t].get(part.id)
            if pose is None:
                continue
            track.append(
                Keyframe(
                    t=t,
                    position=list(pose["position"]),
                    quaternion=list(pose["quaternion"]),
                    scale=list(pose["scale"]),
                    opacity=pose.get("opacity", 1.0),
                )
            )
        objects.append(
            SceneObject(
                id=part.id, geometry=part.geometry, track=track, layer=part.layer
            )
        )

    return Scene(
        title=git.title,
        fps=git.fps,
        duration_frames=git.duration_frames,
        objects=objects,
        layers=[
            Layer(
                str(v["id"]),
                str(v.get("name", v["id"])),
                str(v.get("color", "#8ab4ff")),
            )
            for v in git.layers
        ],
        events=list(git.events),
        source=f"decompiled:{git.source}",
    )


def _same_pose(a: dict, b: dict) -> bool:
    return (
        _close(a["position"], b["position"])
        and _close(a["scale"], b["scale"])
        and _close_quat(a["quaternion"], b["quaternion"])
    )


def _close(a, b) -> bool:
    return all(abs(x - y) <= TOLERANCE for x, y in zip(a, b))


def _close_quat(a, b) -> bool:
    # q and -q are the same rotation, so compare the absolute dot product.
    return abs(abs(sum(x * y for x, y in zip(a, b))) - 1.0) <= TOLERANCE


def round_trip_error(scene: Scene) -> float:
    """Largest pose error after lite -> git -> decode, across all keyframes."""
    git = to_git(scene)
    worst = 0.0
    for obj in scene.objects:
        for k in obj.track:
            want = sample_track(obj.track, k.t)
            got = git.decode(k.t).get(obj.id)
            if got is None:
                return float("inf")
            worst = max(worst, _pose_error(want, got))
    return worst


def _pose_error(a: dict, b: dict) -> float:
    err = max(abs(x - y) for x, y in zip(a["position"], b["position"]))
    err = max(err, max(abs(x - y) for x, y in zip(a["scale"], b["scale"])))
    err = max(
        err,
        abs(abs(sum(x * y for x, y in zip(a["quaternion"], b["quaternion"]))) - 1.0),
    )
    return max(err, abs(a["opacity"] - b["opacity"]))


def matrix_error(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).max())


__all__ = [
    "compose",
    "decompose",
    "matrix_error",
    "round_trip_error",
    "to_git",
    "to_lite",
]
