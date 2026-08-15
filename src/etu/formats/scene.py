"""mmi-lite — a scene as objects, each with a geometry and a keyframe track.

The format is deliberately plain JSON: a reader can open it and see what the
scene contains. Sparse keyframes carry pose (position, quaternion, scale,
opacity) and the viewer interpolates between them, so a 90-frame animation
needs only the frames where something actually changed.

Coordinates are right-handed with +Y up; quaternions are [x, y, z, w] to match
the viewer's convention.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORMAT = "mmi-lite"
VERSION = "0.2"

IDENTITY_QUAT = [0.0, 0.0, 0.0, 1.0]
UNIT_SCALE = [1.0, 1.0, 1.0]


# ── Geometry ────────────────────────────────────────────────────────────
#
# Four kinds, each a flat dataclass. `frames` on the deforming kinds holds
# per-time vertex data for geometry that morphs (a surface bending, a curve
# converging); `points`/`vertices` alone means the shape is fixed and only its
# pose changes.


@dataclass
class PointCloud:
    """Loose points. `colors` is per-point RGB in 0..1, flat like `points`."""

    points: list[float] = field(default_factory=list)
    colors: list[float] | None = None
    point_size: float = 0.05

    kind = "pointcloud"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "points": self.points,
            "point_size": self.point_size,
        }
        if self.colors:
            d["colors"] = self.colors
        return d


@dataclass
class Box:
    """An axis-aligned box. `face_colors` keys are px, nx, py, ny, pz, nz."""

    size: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    color: str = "#8ab4ff"
    face_colors: dict[str, str] | None = None

    kind = "box"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind, "size": self.size, "color": self.color}
        if self.face_colors:
            d["face_colors"] = self.face_colors
        return d


@dataclass
class Surface:
    """A grid mesh of `rows` x `cols` vertices, optionally morphing over time."""

    rows: int = 0
    cols: int = 0
    vertices: list[float] = field(default_factory=list)
    colors: list[float] | None = None
    frames: list[dict[str, Any]] = field(default_factory=list)

    kind = "surface"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "rows": self.rows,
            "cols": self.cols,
            "vertices": self.vertices,
        }
        if self.colors:
            d["colors"] = self.colors
        if self.frames:
            d["frames"] = self.frames
        return d


@dataclass
class Line:
    """A polyline. `frames` lets the curve itself change shape over time."""

    points: list[float] = field(default_factory=list)
    color: str = "#ffffff"
    width: float = 2.0
    frames: list[dict[str, Any]] = field(default_factory=list)

    kind = "line"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "points": self.points,
            "color": self.color,
            "width": self.width,
        }
        if self.frames:
            d["frames"] = self.frames
        return d


GEOMETRY = {g.kind: g for g in (PointCloud, Box, Surface, Line)}


def geometry_from_dict(d: dict[str, Any]) -> PointCloud | Box | Surface | Line:
    """Rebuild a geometry from its dict, ignoring keys the class does not take."""
    kind = d.get("kind", "pointcloud")
    cls = GEOMETRY.get(kind)
    if cls is None:
        raise ValueError(f"unknown geometry kind: {kind!r}")
    fields = {f for f in cls.__dataclass_fields__}
    return cls(**{k: v for k, v in d.items() if k in fields})


# ── Scene ───────────────────────────────────────────────────────────────


@dataclass
class Keyframe:
    """One object's pose at frame `t`. Unset channels inherit the default."""

    t: int
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    quaternion: list[float] | None = None
    scale: list[float] | None = None
    opacity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"t": self.t, "position": self.position}
        if self.quaternion is not None:
            d["quaternion"] = self.quaternion
        if self.scale is not None:
            d["scale"] = self.scale
        if self.opacity is not None:
            d["opacity"] = self.opacity
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Keyframe:
        return Keyframe(
            t=int(d["t"]),
            position=[float(v) for v in d.get("position", [0, 0, 0])],
            quaternion=_opt_floats(d.get("quaternion")),
            scale=_opt_floats(d.get("scale")),
            opacity=None if d.get("opacity") is None else float(d["opacity"]),
        )


@dataclass
class SceneObject:
    """A geometry plus the track that moves it."""

    id: str
    geometry: Any
    track: list[Keyframe] = field(default_factory=list)
    layer: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "geometry": self.geometry.to_dict(),
            "track": [k.to_dict() for k in self.track],
            "layer": self.layer,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> SceneObject:
        return SceneObject(
            id=str(d["id"]),
            geometry=geometry_from_dict(d["geometry"]),
            track=[Keyframe.from_dict(k) for k in d.get("track", [])],
            layer=str(d.get("layer", "default")),
        )


@dataclass
class Layer:
    """A named, toggleable group of objects."""

    id: str
    name: str
    color: str = "#8ab4ff"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "color": self.color}


@dataclass
class Scene:
    """A full mmi-lite scene."""

    title: str
    fps: int = 30
    duration_frames: int = 1
    objects: list[SceneObject] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    source: str = "etu"

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
            "objects": [o.to_dict() for o in self.objects],
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Scene:
        meta = d.get("meta", {})
        return Scene(
            title=str(meta.get("title", "untitled")),
            fps=int(meta.get("fps", 30)),
            duration_frames=int(meta.get("duration_frames", 1)),
            objects=[SceneObject.from_dict(o) for o in d.get("objects", [])],
            layers=[
                Layer(
                    str(v["id"]),
                    str(v.get("name", v["id"])),
                    str(v.get("color", "#8ab4ff")),
                )
                for v in d.get("layers", [])
            ],
            events=list(meta.get("events", [])),
            source=str(meta.get("source", "etu")),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    @staticmethod
    def load(path: str | Path) -> Scene:
        return Scene.from_dict(json.loads(Path(path).read_text()))

    def pose_at(self, obj: SceneObject, t: int) -> dict[str, Any]:
        """Interpolate an object's pose at frame `t`, matching the viewer."""
        return sample_track(obj.track, t)

    def validate(self) -> list[str]:
        """Return a list of problems; empty means the scene is well-formed."""
        problems: list[str] = []
        if self.duration_frames < 1:
            problems.append("duration_frames must be >= 1")
        if self.fps < 1:
            problems.append("fps must be >= 1")
        if not self.objects:
            problems.append("scene has no objects")

        seen: set[str] = set()
        known_layers = {layer.id for layer in self.layers}
        for obj in self.objects:
            if obj.id in seen:
                problems.append(f"duplicate object id: {obj.id!r}")
            seen.add(obj.id)

            if not obj.track:
                problems.append(f"{obj.id!r}: empty track")
            for k in obj.track:
                if not 0 <= k.t < self.duration_frames:
                    problems.append(
                        f"{obj.id!r}: keyframe t={k.t} outside 0..{self.duration_frames - 1}"
                    )
                if len(k.position) != 3:
                    problems.append(
                        f"{obj.id!r}: keyframe t={k.t} position needs 3 values"
                    )
                if k.quaternion is not None and len(k.quaternion) != 4:
                    problems.append(
                        f"{obj.id!r}: keyframe t={k.t} quaternion needs 4 values"
                    )

            if self.layers and obj.layer not in known_layers:
                problems.append(f"{obj.id!r}: layer {obj.layer!r} is not declared")

            problems += _geometry_problems(obj)
        return problems


def _geometry_problems(obj: SceneObject) -> list[str]:
    g = obj.geometry
    out: list[str] = []
    if isinstance(g, PointCloud):
        if len(g.points) % 3:
            out.append(
                f"{obj.id!r}: points length {len(g.points)} is not a multiple of 3"
            )
        if g.colors and len(g.colors) != len(g.points):
            out.append(f"{obj.id!r}: colors length does not match points")
    elif isinstance(g, Surface):
        expected = g.rows * g.cols * 3
        if expected and len(g.vertices) != expected:
            out.append(
                f"{obj.id!r}: expected {expected} vertex values, got {len(g.vertices)}"
            )
    elif isinstance(g, Line):
        if len(g.points) % 3:
            out.append(
                f"{obj.id!r}: line points length {len(g.points)} is not a multiple of 3"
            )
    elif isinstance(g, Box) and len(g.size) != 3:
        out.append(f"{obj.id!r}: box size needs 3 values")
    return out


# ── Track sampling ──────────────────────────────────────────────────────
#
# Kept here rather than in the viewer so Python and JavaScript agree on what a
# track means: position/scale/opacity lerp, rotation slerps, ends clamp.


def sample_track(track: list[Keyframe], t: int) -> dict[str, Any]:
    """Pose at frame `t`: lerp position/scale/opacity, slerp quaternion."""
    if not track:
        return {
            "position": [0.0, 0.0, 0.0],
            "quaternion": list(IDENTITY_QUAT),
            "scale": list(UNIT_SCALE),
            "opacity": 1.0,
        }

    ordered = sorted(track, key=lambda k: k.t)
    if t <= ordered[0].t:
        return _pose(ordered[0])
    if t >= ordered[-1].t:
        return _pose(ordered[-1])

    after = next(i for i, k in enumerate(ordered) if k.t >= t)
    a, b = ordered[after - 1], ordered[after]
    span = b.t - a.t
    u = 0.0 if span == 0 else (t - a.t) / span
    pa, pb = _pose(a), _pose(b)
    return {
        "position": _lerp3(pa["position"], pb["position"], u),
        "quaternion": _slerp(pa["quaternion"], pb["quaternion"], u),
        "scale": _lerp3(pa["scale"], pb["scale"], u),
        "opacity": pa["opacity"] + (pb["opacity"] - pa["opacity"]) * u,
    }


def _pose(k: Keyframe) -> dict[str, Any]:
    return {
        "position": list(k.position),
        "quaternion": list(k.quaternion) if k.quaternion else list(IDENTITY_QUAT),
        "scale": list(k.scale) if k.scale else list(UNIT_SCALE),
        "opacity": 1.0 if k.opacity is None else k.opacity,
    }


def _lerp3(a: list[float], b: list[float], u: float) -> list[float]:
    return [a[i] + (b[i] - a[i]) * u for i in range(3)]


def _slerp(a: list[float], b: list[float], u: float) -> list[float]:
    """Shortest-arc quaternion interpolation, falling back to lerp when close."""
    dot = sum(a[i] * b[i] for i in range(4))
    if dot < 0.0:  # take the short way round
        b = [-v for v in b]
        dot = -dot

    if dot > 0.9995:  # nearly parallel: lerp is stable where slerp is not
        return _normalize([a[i] + (b[i] - a[i]) * u for i in range(4)])

    import math

    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta)
    wa = math.sin((1 - u) * theta) / sin_theta
    wb = math.sin(u * theta) / sin_theta
    return _normalize([a[i] * wa + b[i] * wb for i in range(4)])


def _normalize(q: list[float]) -> list[float]:
    n = sum(v * v for v in q) ** 0.5
    return list(IDENTITY_QUAT) if n == 0 else [v / n for v in q]


def _opt_floats(v: Any) -> list[float] | None:
    return None if v is None else [float(x) for x in v]
