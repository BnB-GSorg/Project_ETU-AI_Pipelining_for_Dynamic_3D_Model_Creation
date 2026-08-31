"""FeatureGraph — "what is on screen and how it moves", with no domain knowledge.

This is the intermediate that lets one lifter handle any subject. Chemistry,
mechanics and maths all reduce to the same thing here: a set of objects, each
with a look and a timeline of states. Nothing in this module knows what a
molecule or a harmonic is, which is exactly why the general lift works on
footage no template covers.

Coordinates are normalised image space: x and y in 0..1 with (0, 0) at the
top-left, size as a fraction of frame width. `depth` in 0..1 is only ever a
guess at front/back ordering (0 = nearest) — it is a hint for the lifter, not
a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Shapes the lifter can turn into a primitive. Anything else becomes a blob.
SHAPES = ("sphere", "box", "disc", "arrow", "tube", "blob", "ring", "plane")


@dataclass
class State:
    """Where an object is, and how it looks, at one timepoint."""

    t: int
    x: float = 0.5
    y: float = 0.5
    size: float = 0.1
    opacity: float = 1.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "t": self.t,
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "opacity": self.opacity,
        }
        if self.note:
            d["note"] = self.note
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> State:
        return State(
            t=int(d.get("t", 0)),
            x=float(d.get("x", 0.5)),
            y=float(d.get("y", 0.5)),
            size=float(d.get("size", 0.1)),
            opacity=float(d.get("opacity", 1.0)),
            note=str(d.get("note", "") or ""),
        )


@dataclass
class FeatureObject:
    """One tracked thing: an identity, a look, and a timeline."""

    id: str
    label: str = ""
    shape: str = "blob"
    color: str = "#8ab4ff"
    depth: float = 0.5
    timeline: list[State] = field(default_factory=list)

    @property
    def first_t(self) -> int:
        return min((s.t for s in self.timeline), default=0)

    @property
    def last_t(self) -> int:
        return max((s.t for s in self.timeline), default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "shape": self.shape,
            "color": self.color,
            "depth": self.depth,
            "timeline": [s.to_dict() for s in self.timeline],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> FeatureObject:
        shape = str(d.get("shape", "blob"))
        return FeatureObject(
            id=str(d.get("id", "obj")),
            label=str(d.get("label", "") or ""),
            shape=shape if shape in SHAPES else "blob",
            color=str(d.get("color", "#8ab4ff")),
            depth=float(d.get("depth", 0.5)),
            timeline=[State.from_dict(s) for s in d.get("timeline", [])],
        )


@dataclass
class FeatureGraph:
    """A whole animation described as objects and their changes."""

    summary: str = ""
    fps: int = 12
    duration: int = 1
    objects: list[FeatureObject] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        return [o.label for o in self.objects if o.label]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "fps": self.fps,
            "duration": self.duration,
            "objects": [o.to_dict() for o in self.objects],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> FeatureGraph:
        objects = [FeatureObject.from_dict(o) for o in d.get("objects", [])]
        duration = int(d.get("duration", 0)) or 1 + max(
            (s.t for o in objects for s in o.timeline), default=0
        )
        return FeatureGraph(
            summary=str(d.get("summary", "") or ""),
            fps=int(d.get("fps", 12)),
            duration=duration,
            objects=objects,
        )

    def describe(self) -> str:
        """A short text rendering, for handing to the reasoning model."""
        lines = [self.summary] if self.summary else []
        for o in self.objects:
            where = ""
            if o.timeline:
                first = o.timeline[0]
                where = f" starting at ({first.x:.2f}, {first.y:.2f})"
            name = o.label or o.id
            lines.append(
                f"{name}: {o.shape}, colour {o.color}, "
                f"{len(o.timeline)} states{where}"
            )
        return "\n".join(lines)

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.objects:
            problems.append("no objects extracted")
        if self.duration < 1:
            problems.append("duration must be >= 1")
        seen: set[str] = set()
        for o in self.objects:
            if o.id in seen:
                problems.append(f"duplicate object id: {o.id!r}")
            seen.add(o.id)
            if not o.timeline:
                problems.append(f"object {o.id!r} has an empty timeline")
        return problems
