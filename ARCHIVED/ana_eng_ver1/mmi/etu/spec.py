"""LessonSpec — the contract between *comprehension* and *authoring*.

Project ETU lifts a flat 2D academic explainer into a 3D interactive scene by
(1) understanding the lesson, then (2) re-authoring it in 3D. This module
defines the structured object that sits between those two halves:

    video  --(comprehend: vision model, FUTURE)-->  LessonSpec  --(author: templates, NOW)-->  Scene

Right now we hand-write LessonSpecs ("template-first"). Later, the comprehension
step (a multimodal model reading keyframes + transcript) emits the same
LessonSpec, and nothing downstream changes. That is the whole point of the seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LessonSpec:
    concept: str                       # template id, e.g. "complex_surface"
    title: str
    params: dict = field(default_factory=dict)   # template-specific parameters
    source_video: str | None = None    # provenance, once comprehension is wired
    rationale: str | None = None        # *why* a 3rd dimension helps here (ETU intent)

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "title": self.title,
            "params": self.params,
            "source_video": self.source_video,
            "rationale": self.rationale,
        }
