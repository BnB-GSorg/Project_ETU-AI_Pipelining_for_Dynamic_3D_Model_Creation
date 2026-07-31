"""
mmi-lite scene format
=====================

An *interim*, human-readable representation of a "dimension-dynamic and
view-dynamic" process. It is the target output of Person A's analysis pipeline
and the strawman input for Person B's `.mmi` compiler.

Design goals
------------
* **View-dynamic**  : geometry lives in 3D; the viewer chooses the camera.
* **Time-dynamic**  : every object carries a sparse *track* of keyframed
                      transforms, so we can scrub through the process.
* **Layered**       : objects belong to named layers that can be toggled.
* **Source-agnostic**: geometry may be a primitive (box), a point cloud, or
                      (later) a Gaussian-splat / mesh blob. The synthetic
                      generator and the neural reconstruction pipeline both
                      emit the same schema.

This is deliberately JSON, not a binary container. It is small, diff-able and
easy to inspect during research. Person B's `.mmi` is expected to be the
compiled/binary descendant of this schema.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

FORMAT_NAME = "mmi-lite"
FORMAT_VERSION = "0.1"


@dataclass
class Keyframe:
    """A single sampled transform at frame index ``t``.

    Rotations are unit quaternions in ``[x, y, z, w]`` order (Three.js order).
    Position is in scene units. ``scale`` is optional and defaults to identity.
    ``opacity`` (0..1) is optional and drives object lifetime: it lets an object
    fade in/out and lets a merged or vanished object disappear (opacity 0 == not
    drawn). It defaults to fully opaque; the viewer interpolates it between
    keyframes (unlike pose, which is step-held).
    """

    t: int
    position: list[float]
    quaternion: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    scale: list[float] | None = None
    opacity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"t": self.t, "position": _round(self.position)}
        d["quaternion"] = _round(self.quaternion, 6)
        if self.scale is not None:
            d["scale"] = _round(self.scale)
        if self.opacity is not None:
            d["opacity"] = round(float(self.opacity), 4)
        return d


@dataclass
class BoxGeometry:
    """A unit-ish box with independently colored faces.

    Faces are keyed ``px, nx, py, ny, pz, nz`` (+X, -X, +Y, ...). This is enough
    to render a Rubik's cubie; the pipeline will mostly emit ``PointCloud`` or
    splat geometry instead.
    """

    size: list[float]
    face_colors: dict[str, str]
    kind: str = "box"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "size": self.size, "face_colors": self.face_colors}


@dataclass
class PointCloudGeometry:
    """A static point cloud in the object's local frame.

    ``points`` is a flat ``[x0,y0,z0, x1,y1,z1, ...]`` list; ``colors`` is an
    optional parallel flat ``[r,g,b, ...]`` list in 0..1. This is the natural
    output of SfM / Gaussian-splat reconstruction once a per-object pose is
    factored out.
    """

    points: list[float]
    colors: list[float] | None = None
    point_size: float = 0.02
    frames: list[dict] | None = None      # morph: [{"t","positions","colors"?}]
    kind: str = "pointcloud"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "points": _round(self.points, 5),
            "point_size": self.point_size,
        }
        if self.colors is not None:
            d["colors"] = _round(self.colors, 4)
        if self.frames is not None:
            d["frames"] = [_frame_to_dict(f) for f in self.frames]
        return d


@dataclass
class LineGeometry:
    """A polyline. Either static (``points``) or *morphing* (``frames``).

    Morphing geometry is what math visualization needs: a curve that deforms
    over time. ``frames`` is a sparse list of ``{"t": int, "points": [...]}``
    keyframes with a *constant* vertex count; the viewer linearly interpolates
    vertex positions between them (morph-target animation).
    """

    color: str = "#5b8cff"
    width: float = 2.0
    points: list[float] | None = None
    frames: list[dict] | None = None
    kind: str = "line"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind, "color": self.color, "width": self.width}
        if self.points is not None:
            d["points"] = _round(self.points, 5)
        if self.frames is not None:
            d["frames"] = [{"t": int(f["t"]), "points": _round(f["points"], 5)} for f in self.frames]
        return d


@dataclass
class SurfaceGeometry:
    """A ``rows x cols`` grid mesh. Static (``positions``) or morphing (``frames``).

    Vertex order is row-major. Optional per-vertex ``colors`` (0..1) drive a
    height/value colormap. The viewer triangulates the grid once and morphs the
    position (and color) buffers over time.
    """

    rows: int
    cols: int
    color: str = "#5b8cff"
    opacity: float = 1.0
    wireframe: bool = False
    positions: list[float] | None = None
    colors: list[float] | None = None
    frames: list[dict] | None = None
    kind: str = "surface"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind, "rows": self.rows, "cols": self.cols,
            "color": self.color, "opacity": self.opacity, "wireframe": self.wireframe,
        }
        if self.positions is not None:
            d["positions"] = _round(self.positions, 4)
        if self.colors is not None:
            d["colors"] = _round(self.colors, 3)
        if self.frames is not None:
            d["frames"] = [_frame_to_dict(f) for f in self.frames]
        return d


def _frame_to_dict(f: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"t": int(f["t"]), "positions": _round(f["positions"], 4)}
    if f.get("colors") is not None:
        out["colors"] = _round(f["colors"], 3)
    return out


@dataclass
class SceneObject:
    """A trackable sub-object of the process (e.g. one cubie, one part)."""

    id: str
    geometry: BoxGeometry | PointCloudGeometry | LineGeometry | SurfaceGeometry
    track: list[Keyframe]
    layer: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer,
            "geometry": self.geometry.to_dict(),
            "track": [k.to_dict() for k in self.track],
        }


@dataclass
class Layer:
    id: str
    name: str
    color: str = "#888888"
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Annotation:
    """A 3D pin/label shown around a given time window."""

    t: int
    position: list[float]
    text: str
    t_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"t": self.t, "position": _round(self.position), "text": self.text}
        if self.t_end is not None:
            d["t_end"] = self.t_end
        return d


@dataclass
class Scene:
    title: str
    fps: int
    duration_frames: int
    objects: list[SceneObject] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    # Timeline of human-readable events, shown as a HUD ("Move 3: R'").
    events: list[dict[str, Any]] = field(default_factory=list)
    source: str = "synthetic"
    coordinate_system: str = "right-handed-y-up"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "meta": {
                "title": self.title,
                "fps": self.fps,
                "duration_frames": self.duration_frames,
                "source": self.source,
                "coordinate_system": self.coordinate_system,
                "events": self.events,
            },
            "layers": [l.to_dict() for l in self.layers],
            "objects": [o.to_dict() for o in self.objects],
            "annotations": [a.to_dict() for a in self.annotations],
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty == valid)."""
        problems: list[str] = []
        layer_ids = {l.id for l in self.layers}
        for obj in self.objects:
            if obj.layer not in layer_ids and obj.layer != "default":
                problems.append(f"object {obj.id!r} references unknown layer {obj.layer!r}")
            if not obj.track:
                problems.append(f"object {obj.id!r} has an empty track")
            for k in obj.track:
                if not (0 <= k.t < self.duration_frames):
                    problems.append(f"object {obj.id!r} keyframe t={k.t} out of range")
                if len(k.quaternion) != 4:
                    problems.append(f"object {obj.id!r} keyframe t={k.t} bad quaternion")
                if k.opacity is not None and not (0.0 <= k.opacity <= 1.0):
                    problems.append(f"object {obj.id!r} keyframe t={k.t} opacity {k.opacity} out of [0,1]")
        return problems


def _round(values: list[float], ndigits: int = 4) -> list[float]:
    return [round(float(v), ndigits) for v in values]
