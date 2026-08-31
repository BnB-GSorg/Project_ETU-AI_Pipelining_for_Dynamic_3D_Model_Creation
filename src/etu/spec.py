"""LessonSpec — the handover between understanding a lesson and authoring it.

Comprehension decides *what* the video teaches; a template decides *how* to
show it in 3D. This is the only thing that crosses between them, so either
side can be replaced without touching the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LessonSpec:
    """A concept id plus the parameters that author its 3D scene."""

    concept: str
    title: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    confidence: float = 1.0
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "title": self.title,
            "params": self.params,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "source": self.source,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> LessonSpec:
        return LessonSpec(
            concept=str(d.get("concept", "")),
            title=str(d.get("title", "")),
            params=dict(d.get("params", {})),
            rationale=str(d.get("rationale", "")),
            confidence=float(d.get("confidence", 1.0)),
            source=str(d.get("source", "")),
        )
