"""Registry of ETU math templates.

A template is ``build(params: dict) -> Scene``. To add a concept family, write a
module with a ``build`` function and register it here. The (future) comprehension
step chooses a ``concept`` (registry key) and fills ``params`` from a video.
"""

from __future__ import annotations

from collections.abc import Callable

from mmi.etu.templates import (
    complex_surface,
    fourier_stack,
    graph_surface,
    linear_transform,
    parametric_surface,
    taylor_series,
    vector_field,
)
from mmi.formats.mmi_scene import Scene

REGISTRY: dict[str, Callable[[dict], Scene]] = {
    "graph_surface": graph_surface.build,
    "complex_surface": complex_surface.build,
    "fourier_stack": fourier_stack.build,
    "taylor_series": taylor_series.build,
    "vector_field": vector_field.build,
    "linear_transform": linear_transform.build,
    "parametric_surface": parametric_surface.build,
}


def available() -> list[str]:
    return sorted(REGISTRY)
