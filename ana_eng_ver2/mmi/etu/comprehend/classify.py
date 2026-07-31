"""Closed-set classification: text evidence -> LessonSpec (or abstain).

The model is constrained to pick one catalog concept (or "none") and fill its
declared params. Output is strict JSON, then validated/clamped against the
catalog, so a wrong or over-confident answer can't produce invalid geometry.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from mmi.etu.comprehend import catalog
from mmi.etu.comprehend.llm import LLMConfig, chat, make_config
from mmi.etu.spec import LessonSpec

_SYSTEM = """You map a 2D math explainer video to ONE 3D visualization template, \
for "Project ETU" (lift 2D lessons into 3D).

You are given text evidence (narration transcript and/or on-screen text). Choose \
exactly one concept from the catalog whose topic matches, or "none" if none fit.

Rules:
- Pick "none" if the evidence is unrelated to the available concepts. Do not force a fit.
- Only use parameter keys and values allowed by the chosen concept's schema.
  For enum params, pick the closest allowed value. Omit params you are unsure about
  (defaults will be used).
- confidence is your calibrated probability (0..1) that this concept is correct.

CATALOG:
%s

Respond with STRICT JSON only, this exact shape:
{"concept": "<id or 'none'>", "params": {...}, "confidence": <0..1>, "rationale": "<one sentence>"}"""


@dataclass
class Comprehension:
    spec: LessonSpec | None          # None => abstained
    concept: str                     # chosen concept or "none"
    confidence: float
    rationale: str
    raw: dict                        # raw model JSON, for debugging


def build_prompt(evidence_text: str) -> tuple[str, str]:
    system = _SYSTEM % json.dumps(catalog.prompt_catalog(), indent=2)
    return system, f"EVIDENCE:\n{evidence_text}"


def comprehend(
    evidence_text: str,
    cfg: LLMConfig | None = None,
    chat_fn: Callable[[str, str], str] | None = None,
    min_confidence: float = 0.45,
    source_video: str | None = None,
) -> Comprehension:
    system, user = build_prompt(evidence_text)
    if chat_fn is None:
        cfg = cfg or make_config("deepseek")
        chat_fn = lambda s, u: chat(cfg, s, u, json_mode=True)  # noqa: E731

    raw_text = chat_fn(system, user)
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return Comprehension(None, "none", 0.0, "model returned non-JSON", {"text": raw_text})

    concept = str(raw.get("concept", "none"))
    confidence = float(raw.get("confidence", 0.0) or 0.0)
    rationale = str(raw.get("rationale", ""))

    if concept not in catalog.CATALOG:
        return Comprehension(None, "none", confidence, rationale or "no matching concept", raw)
    if confidence < min_confidence:
        return Comprehension(None, concept, confidence, rationale or "below confidence threshold", raw)

    params = catalog.validate_params(concept, raw.get("params", {}) or {})
    spec = LessonSpec(concept=concept, title="", params=params, source_video=source_video, rationale=rationale)
    return Comprehension(spec, concept, confidence, rationale, raw)
