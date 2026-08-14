"""Stage-transition guidance — optional human-in-the-loop NL intervention.

ETU runs fully automatic: CV extracts objects, the reasoning model labels them,
the lifter authors a 3D scene. But some stage-to-stage changes are genuinely
hard to infer from a single 2D view — an object split/merge, a rigid rotation,
an occlusion. This module adds an OPTIONAL interactive hook: at each transition
between consecutive stages (event timepoints), the user may type a
natural-language description of HOW the system changed. That text is folded into
the SAME reasoning model (the sole LLM) as extra evidence, and the brain may
correct object labels/relations accordingly. The notes are also persisted as
scene events (HUD) so the human's instruction is visible in the viewer.

Empty input = "let the model guess": the automatic behavior is unchanged.
Guidance is best-effort — it must never break the automatic path, so every
network/reasoning step degrades to a no-op on failure.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from mmi.etu.comprehend.llm import LLMConfig, chat, make_config
from mmi.etu.understand.schema import FeatureGraph


@dataclass
class TransitionNote:
    """A user's natural-language description of one stage→stage change."""
    t_from: int
    t_to: int
    text: str


def stage_boundaries(fg: FeatureGraph) -> list[tuple[int, int]]:
    """The consecutive stage timepoints across the whole graph.

    A "stage" is any timepoint where at least one object changes state; the
    transition between two consecutive stages is what the user may annotate.
    """
    ts = sorted({s.t for o in fg.objects for s in o.timeline})
    return [(ts[i], ts[i + 1]) for i in range(len(ts) - 1)]


def _describe(fg: FeatureGraph, t: int) -> str:
    """One-line description of which objects are present at a given stage."""
    bits = []
    for o in fg.objects:
        if any(s.t == t for s in o.timeline):
            bits.append(f"{o.id}({o.label or o.shape})")
    return ", ".join(bits) if bits else "(empty)"


def make_prompt(fg: FeatureGraph, t_from: int, t_to: int) -> str:
    """The CLI prompt string shown to the user at one stage transition."""
    return (
        f"\n== stage {t_from} -> {t_to} ==\n"
        f"  before: {_describe(fg, t_from)}\n"
        f"  after : {_describe(fg, t_to)}\n"
        f"describe how the system changed (Enter = let the model guess): "
    )


def collect_guidance(
    fg: FeatureGraph,
    prompt: Callable[[str], str | None] | None = None,
    *,
    interactive: bool = False,
) -> list[TransitionNote]:
    """Walk every stage transition; optionally ask the user how it changed.

    `prompt` defaults to `input()`. Only non-empty answers become notes.
    Not interactive -> no notes (the pure automatic path).
    """
    if not interactive or not fg.objects:
        return []
    if prompt is None:
        prompt = input
    notes: list[TransitionNote] = []
    for t_from, t_to in stage_boundaries(fg):
        try:
            text = prompt(make_prompt(fg, t_from, t_to))
        except (EOFError, KeyboardInterrupt):
            break  # skip the rest, fall through to the automatic path
        text = (text or "").strip()
        if text:
            notes.append(TransitionNote(t_from, t_to, text))
    return notes


def guidance_text(notes: list[TransitionNote]) -> str:
    """Render the notes as a compact block for the reasoning model."""
    return "\n".join(f"- stage {n.t_from}->{n.t_to}: {n.text}" for n in notes)


_REFINE_SYSTEM = """You are the reasoning model of Project ETU. You are given a \
FeatureGraph (objects with ids, labels, shapes, colors) and a human's \
natural-language notes describing how the system changed between stages. \
Correct any object labels the human's notes clarify, and fill in the \
"relations" between objects if the notes imply them.

Respond with STRICT JSON only, this exact shape:
{"labels": {"<object_id>": "<corrected label>"}, "relations": [{"a": "<id>", "b": "<id>", "kind": "<bond|flow|contains|...>"}]}

If nothing needs correcting, respond {"labels": {}, "relations": []}."""


def refine(
    fg: FeatureGraph,
    notes: list[TransitionNote],
    cfg: LLMConfig | None = None,
    chat_fn: Callable[[str, str], str] | None = None,
) -> dict:
    """Ask the reasoning model to correct labels/relations from the notes.

    Returns a dict of refinements (possibly empty). Best-effort: any failure
    degrades to ``{}`` rather than raising into the pipeline.
    """
    if not notes:
        return {}
    if chat_fn is None:
        cfg = cfg or make_config("deepseek")
        chat_fn = lambda s, u: chat(cfg, s, u, json_mode=True)  # noqa: E731

    objs = [
        {"id": o.id, "label": o.label, "shape": o.shape, "color": o.color}
        for o in fg.objects
    ]
    user = (
        "FEATURE GRAPH OBJECTS:\n"
        + json.dumps(objs, indent=2)
        + "\n\nUSER NOTES:\n"
        + guidance_text(notes)
    )
    try:
        raw = chat_fn(_REFINE_SYSTEM, user)
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def apply_refinements(fg: FeatureGraph, refinements: dict) -> None:
    """Apply brain-authored label/relation corrections onto the FeatureGraph."""
    if not isinstance(refinements, dict):
        return
    labels = refinements.get("labels") or {}
    if isinstance(labels, dict):
        for o in fg.objects:
            if o.id in labels and labels[o.id]:
                o.label = str(labels[o.id])
    rels = refinements.get("relations") or []
    if isinstance(rels, list):
        fg.relations = [dict(r) for r in rels if isinstance(r, dict)]
