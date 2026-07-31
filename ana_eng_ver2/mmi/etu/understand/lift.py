"""Generic lifter: FeatureGraph -> 3D/4D mmi-lite Scene (domain-agnostic).

Turns the universal object-and-change description into an orbitable, scrubbable
scene that works for ANY animation:

- each object becomes a 3D primitive (sphere/box/tube/arrow/...) chosen from its
  shape hint, colored, sized;
- it moves over time via a track built from the object's timeline (x,y -> scene
  plane; the model's relative `depth` -> a small spread on the 3rd axis so
  orbiting reveals layering);
- each object also leaves a faint **trajectory trail** (its path through space),
  so the whole process is legible at once — "different timepoints" made spatial.

The 3rd spatial axis is an honest *approximation* (2D->3D depth is ambiguous);
motion and time are faithful. Where a domain template exists, use that instead
for a correct lift.
"""

from __future__ import annotations

import numpy as np

from mmi.etu.understand.schema import FeatureGraph, FeatureObject
from mmi.formats.mmi_scene import (
    BoxGeometry,
    Keyframe,
    Layer,
    LineGeometry,
    PointCloudGeometry,
    Scene,
    SceneObject,
)

_DEPTH_SPREAD = 2.4
_PLANE_W, _PLANE_H = 6.0, 4.0
_SUBDIV = 6           # playback frames between consecutive event keyframes (the viewer interpolates these)


def _to_scene(x: float, y: float, depth: float) -> list[float]:
    # normalized image (top-left origin) -> scene (y up), depth -> z spread
    return [(x - 0.5) * _PLANE_W, (0.5 - y) * _PLANE_H, (0.5 - depth) * _DEPTH_SPREAD]


def _sphere_points(n: int = 600) -> tuple[list[float], int]:
    # Filled fibonacci ball of unit diameter (radius 0.5). Filling the volume
    # (radius scaled by cube-root) instead of a thin shell makes the object read
    # as a solid, clearly-visible blob rather than a faint sparse outline.
    pts = []
    ga = np.pi * (3 - np.sqrt(5))
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = np.sqrt(max(0.0, 1 - y * y))
        th = ga * i
        rad = 0.5 * ((i + 0.5) / n) ** (1 / 3)   # 0..0.5, denser packing toward the surface
        pts += [rad * np.cos(th) * r, rad * y, rad * np.sin(th) * r]
    return pts, n


def _hex_to_rgb01(c: str) -> list[float]:
    c = c.lstrip("#")
    if len(c) != 6:
        return [0.55, 0.7, 1.0]
    return [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _primitive(obj: FeatureObject):
    """Build a unit-size primitive for the object; track scale will size it."""
    shape = obj.shape
    if shape in ("sphere", "blob", "disc", "ring"):
        pts, n = _sphere_points()
        return PointCloudGeometry(points=pts, colors=_hex_to_rgb01(obj.color) * n, point_size=0.09)
    if shape in ("tube", "arrow"):
        # a short segment along x; arrow gets a couple of head points
        base = [[-0.5, 0, 0], [0.5, 0, 0]]
        if shape == "arrow":
            base += [[0.3, 0.15, 0], [0.5, 0, 0], [0.3, -0.15, 0]]
        return LineGeometry(color=obj.color, width=3.0, points=np.array(base).flatten().tolist())
    # box / plane / default
    sz = [1.0, 1.0, 0.15] if shape == "plane" else [1.0, 1.0, 1.0]
    return BoxGeometry(size=sz, face_colors={f: obj.color for f in ("px", "nx", "py", "ny", "pz", "nz")})


def _track(obj: FeatureObject, n_ordinal: int, duration: int, subdiv: int) -> list[Keyframe]:
    """Build the object's pose track, with opacity driving its lifetime.

    The extracted timepoints are *event* keyframes (the moments the picture
    changed); we place them ``subdiv`` frames apart on the playback timeline and
    let the viewer interpolate the gaps — "keyframes at the change, calculate the
    in-between." Pose (position/scale) lerps and rotation slerps between them.

    Opacity drives lifetime: an object is only "alive" between its first and last
    observed state. Before it appears and after it leaves/merges we emit opacity-0
    keyframes (a ``subdiv`` window, so it fades rather than pops) instead of
    leaving a stale primitive on screen. Per-state opacity is carried through too.
    """
    states = sorted(obj.timeline, key=lambda s: s.t)
    if not states:
        return [Keyframe(0, _to_scene(0.5, 0.5, obj.depth))]

    first_o, last_o = states[0].t, states[-1].t
    # Lifetime is non-trivial when the object is born late, dies early, or fades.
    needs_lifetime = first_o > 0 or last_o < n_ordinal - 1 or any(s.opacity < 1.0 for s in states)

    def frame_of(t: int) -> int:
        return max(0, min(t * subdiv, duration - 1))

    kfs: list[Keyframe] = []
    if needs_lifetime and first_o > 0:
        # hidden, fading in over the subdiv window just before it appears
        kfs.append(Keyframe(t=max(0, frame_of(first_o) - subdiv),
                            position=_to_scene(states[0].x, states[0].y, obj.depth), opacity=0.0))

    for s in states:
        pos = _to_scene(s.x, s.y, obj.depth)
        k = max(0.05, s.size) * 6.0           # size fraction -> scene scale
        kfs.append(Keyframe(
            t=frame_of(s.t), position=pos, scale=[k, k, k],
            opacity=(s.opacity if needs_lifetime else None)))

    if needs_lifetime and last_o < n_ordinal - 1:
        # fades out over the subdiv window after its last sighting
        last = states[-1]
        kfs.append(Keyframe(t=min(duration - 1, frame_of(last_o) + subdiv),
                            position=_to_scene(last.x, last.y, obj.depth), opacity=0.0))

    return kfs


def _trajectory(obj: FeatureObject) -> list[float] | None:
    if len(obj.timeline) < 2:
        return None
    pts = []
    for s in sorted(obj.timeline, key=lambda s: s.t):
        pts += _to_scene(s.x, s.y, obj.depth)
    return pts


def lift(fg: FeatureGraph, title: str | None = None) -> Scene:
    n_ordinal = max(2, fg.duration)
    # Spread the event timepoints onto a finer timeline so the viewer interpolates
    # the in-between frames (smooth motion) instead of every frame being a keyframe.
    duration = (n_ordinal - 1) * _SUBDIV + 1
    objects: list[SceneObject] = []
    layers = [Layer("objects", "Objects", "#8ab4ff"), Layer("trails", "Trajectory trails", "#5b6677")]

    for obj in fg.objects:
        objects.append(SceneObject(
            id=obj.id, geometry=_primitive(obj), track=_track(obj, n_ordinal, duration, _SUBDIV), layer="objects"))
        traj = _trajectory(obj)
        if traj is not None:
            objects.append(SceneObject(
                id=f"{obj.id}__trail",
                geometry=LineGeometry(color=obj.color, width=1.5, points=traj),
                track=[Keyframe(0, [0, 0, 0])], layer="trails"))

    events = [{"t": 0, "label": fg.summary[:80]}] if fg.summary else []
    return Scene(
        title=title or (fg.summary[:60] or "Lifted 2D animation"),
        fps=max(1, fg.fps) * _SUBDIV, duration_frames=duration, objects=objects, layers=layers,
        events=events, source="etu:general-lift")
