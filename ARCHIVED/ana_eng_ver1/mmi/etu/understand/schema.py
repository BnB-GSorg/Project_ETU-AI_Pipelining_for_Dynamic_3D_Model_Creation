"""FeatureGraph — the universal "objects + features + changes" representation.

This is the domain-agnostic intermediate that makes ETU general: ANY 2D
animation (math, chemistry, medical, mechanical) is described as a set of objects,
each with visual features and a timeline of how it changes. The vision extractor
fills it; the generic lifter turns it into a 3D/4D scene. It deliberately does NOT
encode any domain knowledge — it is just "what is on screen and how it moves."

Coordinates are normalized image space: x,y in [0,1] with (0,0) = top-left,
size in [0,1] as a fraction of frame width. depth in [0,1] is the vision model's
*guess* at relative front/back ordering (0 = nearest), used only as a hint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Shapes the lifter knows how to turn into a 3D primitive. Unknown -> "blob".
SHAPES = ["sphere", "box", "disc", "arrow", "tube", "blob", "ring", "plane"]


@dataclass
class State:
    t: int                       # timepoint index (0..duration-1)
    x: float                     # normalized image x (0..1)
    y: float                     # normalized image y (0..1, top-left origin)
    size: float = 0.1            # fraction of frame
    opacity: float = 1.0
    label: str | None = None     # optional per-moment state note ("bonded", "excited")


@dataclass
class FeatureObject:
    id: str
    label: str                   # what it is, in plain words ("red ball", "electron")
    shape: str = "blob"          # one of SHAPES
    color: str = "#8ab4ff"
    depth: float = 0.5           # relative front/back guess (0 = nearest)
    timeline: list[State] = field(default_factory=list)


@dataclass
class FeatureGraph:
    summary: str = ""            # one line: what mechanism the video shows
    fps: int = 12
    duration: int = 1            # number of timepoints
    objects: list[FeatureObject] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)  # optional: {a,b,kind}

    # ------- (de)serialization for the vision model + debugging -------
    @staticmethod
    def from_dict(d: dict[str, Any]) -> "FeatureGraph":
        objs = []
        for o in d.get("objects", []):
            tl = [State(
                t=int(s.get("t", 0)), x=float(s.get("x", 0.5)), y=float(s.get("y", 0.5)),
                size=float(s.get("size", 0.1)), opacity=float(s.get("opacity", 1.0)),
                label=s.get("label"),
            ) for s in o.get("timeline", [])]
            objs.append(FeatureObject(
                id=str(o.get("id", "obj")), label=str(o.get("label", "object")),
                shape=str(o.get("shape", "blob")), color=str(o.get("color", "#8ab4ff")),
                depth=float(o.get("depth", 0.5)), timeline=tl,
            ))
        dur = int(d.get("duration", 0)) or (1 + max((s.t for o in objs for s in o.timeline), default=0))
        return FeatureGraph(summary=str(d.get("summary", "")), fps=int(d.get("fps", 12)),
                            duration=dur, objects=objs, relations=list(d.get("relations", [])))

    def validate(self) -> list[str]:
        problems = []
        if not self.objects:
            problems.append("no objects extracted")
        for o in self.objects:
            if not o.timeline:
                problems.append(f"object {o.id!r} has empty timeline")
        return problems


# JSON schema description embedded in the extractor prompt (kept in sync with above).
SCHEMA_FOR_PROMPT = json.dumps({
    "summary": "one sentence: what process/mechanism the video shows",
    "fps": "integer, playback speed (e.g. 12)",
    "duration": "integer, number of timepoints you describe",
    "objects": [{
        "id": "short unique id",
        "label": "what it is in plain words",
        "shape": "one of: " + ", ".join(SHAPES),
        "color": "#rrggbb",
        "depth": "0..1 relative front(0)/back(1) guess",
        "timeline": [{"t": "int timepoint", "x": "0..1 left->right", "y": "0..1 top->bottom",
                      "size": "0..1 of frame", "opacity": "0..1", "label": "optional state note"}],
    }],
    "relations": [{"a": "object id", "b": "object id", "kind": "e.g. bond, flow, contains"}],
}, indent=2)
