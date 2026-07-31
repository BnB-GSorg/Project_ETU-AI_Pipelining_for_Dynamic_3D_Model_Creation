"""Vision extractor: 2D animation frames -> FeatureGraph (domain-agnostic).

This is the general "transfer the objects' main features and their changes"
step. It asks a vision model to describe, for ANY animation, the objects on
screen and how they move/scale/appear over time — with no domain assumptions.
The result is the universal FeatureGraph the lifter turns into 3D/4D.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from mmi.etu.comprehend.llm import LLMConfig, make_config, vision_chat
from mmi.etu.understand.identity import reconcile
from mmi.etu.understand.sampling import select_by_change
from mmi.etu.understand.schema import SCHEMA_FOR_PROMPT, FeatureGraph

_SYSTEM = f"""You analyze a 2D explainer/simulator animation and extract a \
structured, domain-agnostic description of its objects and how they change over time.

You are shown frames sampled in time order. Identify the distinct visual objects \
(shapes, particles, parts, regions). For each, track its position, size and \
appearance across the frames. Make NO domain assumptions and invent nothing not \
visible — just report what is on screen and how it moves.

Use normalized coordinates: x,y in [0,1] with (0,0) at the TOP-LEFT; size as a \
fraction of frame width. Use one integer timepoint per sampled frame, starting at 0.

Output STRICT JSON ONLY, matching this schema (no prose, no code fences):
{SCHEMA_FOR_PROMPT}"""


def _parse_json(text: str) -> dict:
    """Tolerant JSON extraction (handles ```json fences / surrounding prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(text[i:j + 1])
        raise


def extract(
    frames: list[Path],
    cfg: LLMConfig | None = None,
    chat_fn: Callable[[str, str, list[str]], str] | None = None,
    hint: str = "",
    max_images: int = 8,
) -> FeatureGraph:
    if not frames:
        return FeatureGraph()
    # change-driven sampling: dense where the animation changes, sparse where it's
    # still — so the model sees the moments that matter, not arbitrary cuts.
    picked = select_by_change(frames, max_images)
    user = (f"Context hint: {hint}\n\n" if hint else "") + \
        f"Here are {len(picked)} frames in time order (timepoints 0..{len(picked)-1}). Extract the FeatureGraph."

    if chat_fn is None:
        cfg = cfg or make_config("gemini")
        chat_fn = lambda s, u, imgs: vision_chat(cfg, s, u, imgs)  # noqa: E731

    raw = chat_fn(_SYSTEM, user, [str(p) for p in picked])
    # stitch any frame-to-frame ID drift before the lifter sees it
    return reconcile(FeatureGraph.from_dict(_parse_json(raw)))
