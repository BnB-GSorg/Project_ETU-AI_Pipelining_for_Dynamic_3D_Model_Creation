"""Author step: LessonSpec -> mmi-lite Scene, by dispatching to a template.

This is the deterministic half of ETU. The comprehension half (video -> LessonSpec)
will be added later; it only needs to produce a LessonSpec whose ``concept`` is a
known template key. Keeping this dispatch tiny and pure is the point — swapping
hand-written specs for model-generated ones changes nothing here.
"""

from __future__ import annotations

from mmi.etu.spec import LessonSpec
from mmi.etu.templates import REGISTRY, available
from mmi.formats.mmi_scene import Scene


def synthesize(spec: LessonSpec) -> Scene:
    if spec.concept not in REGISTRY:
        raise KeyError(f"unknown concept {spec.concept!r}; available: {available()}")
    scene = REGISTRY[spec.concept](spec.params)
    if spec.title:
        scene.title = spec.title
    problems = scene.validate()
    if problems:
        raise ValueError(f"template {spec.concept!r} produced an invalid scene: {problems}")
    return scene
