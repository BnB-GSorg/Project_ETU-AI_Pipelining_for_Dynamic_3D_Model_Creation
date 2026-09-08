"""What the engine knows about each kind of object it can model.

One concept per entry: how to build it, what its operations are, what "done"
looks like. Adding a second concept means adding one entry here and one module
beside `rubiks.py` — no registration ceremony, just a dict.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from etu.kb import rubiks
from etu.model import Model


@dataclass
class ConceptInfo:
    """Everything needed to build an object of this kind and operate on it."""

    name: str
    summary: str
    properties: dict[str, Any] = field(default_factory=dict)
    target: str = ""
    operations: list[str] = field(default_factory=list)
    build: Callable[..., Model] | None = None
    solve: Callable[[list[str]], list[str]] | None = None
    layers: list[dict[str, str]] = field(default_factory=list)

    def describe(self) -> str:
        return "\n".join(
            [
                f"{self.name} — {self.summary}",
                f"  goal      : {self.target}",
                f"  operations: {' '.join(self.operations)}",
                *[f"  {k:<10}: {v}" for k, v in self.properties.items()],
            ]
        )


CONCEPTS: dict[str, ConceptInfo] = {
    "rubiks_cube": ConceptInfo(
        name="rubiks_cube",
        summary="A 3x3x3 twisty puzzle of 26 cubies in six colours.",
        properties={
            "parts": 26,
            "colours": 6,
            "faces": "U D L R F B",
            "modifiers": "' = anticlockwise, 2 = half turn",
        },
        target="every face a single solid colour",
        operations=rubiks.operations(),
        build=rubiks.build_cube,
        # The honest solver for a scramble we know: undo it. A general solver
        # (Kociemba) would be needed for a state read cold from a photo.
        solve=rubiks.invert,
        layers=rubiks.layers(),
    )
}

ALIASES = {
    "rubik": "rubiks_cube",
    "rubiks": "rubiks_cube",
    "rubik's cube": "rubiks_cube",
    "rubiks cube": "rubiks_cube",
    "cube": "rubiks_cube",
    "3x3": "rubiks_cube",
}


def lookup(concept: str) -> ConceptInfo | None:
    """Find a concept by name or common alias. None when we do not know it."""
    key = concept.strip().lower()
    return CONCEPTS.get(ALIASES.get(key, key))


def known() -> list[str]:
    return sorted(CONCEPTS)


def search(text: str) -> ConceptInfo | None:
    """Find the concept a free-text phrase is talking about."""
    haystack = text.strip().lower()
    for alias, name in sorted(ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in haystack:
            return CONCEPTS[name]
    for name, info in CONCEPTS.items():
        if name in haystack:
            return info
    return None
