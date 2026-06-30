"""Router — the universal ETU entry point for any 2D animation.

Strategy (best of both worlds, ~one vision call + one cheap text call):

  1. EXTRACT a domain-agnostic FeatureGraph from the frames (general understanding).
  2. UPGRADE: if the content confidently matches a known closed-set template
     (judged from transcript + the extracted summary/labels), author that template
     for a *correct, high-quality* lift.
  3. FALLBACK: otherwise LIFT the FeatureGraph generically — works on anything,
     honestly approximate on depth.

So coverage is universal (everything gets at least the general lift) while known
domains get the reliable, correct template.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mmi.etu import synthesize
from mmi.etu.comprehend import comprehend
from mmi.etu.comprehend.llm import LLMConfig
from mmi.etu.understand import FeatureGraph, extract, lift
from mmi.formats.mmi_scene import Scene


@dataclass
class RouterResult:
    scene: Scene | None
    method: str                 # "template" | "general" | "none"
    concept: str
    confidence: float
    rationale: str
    feature_graph: FeatureGraph | None


def comprehend_any(
    frames: list[Path] | None = None,
    transcript_text: str = "",
    hint: str = "",
    brain_cfg: LLMConfig | None = None,
    vision_cfg: LLMConfig | None = None,
    prefer: str = "auto",        # "auto" | "template" | "general"
    min_confidence: float = 0.55,
    chat_brain: Callable[[str, str], str] | None = None,
    chat_eye: Callable[[str, str, list[str]], str] | None = None,
) -> RouterResult:
    fg: FeatureGraph | None = None
    if frames:
        fg = extract(frames, cfg=vision_cfg, chat_fn=chat_eye, hint=hint)

    # 1+2) try the closed-set template upgrade (unless caller forces general)
    if prefer != "general":
        parts = [transcript_text, hint]
        if fg:
            parts.append(fg.summary)
            parts += [o.label for o in fg.objects]
        evidence = "\n".join(p for p in parts if p).strip()
        if evidence:
            c = comprehend(evidence, cfg=brain_cfg, chat_fn=chat_brain, min_confidence=min_confidence)
            if c.spec:
                return RouterResult(synthesize(c.spec), "template", c.concept, c.confidence, c.rationale, fg)
            if prefer == "template":
                return RouterResult(None, "none", c.concept, c.confidence, c.rationale, fg)

    # 3) general fallback
    if fg and not fg.validate():
        return RouterResult(lift(fg), "general", "general-lift", 1.0, "lifted FeatureGraph", fg)

    reason = "no frames to extract from" if not fg else f"invalid FeatureGraph: {fg.validate()}"
    return RouterResult(None, "none", "none", 0.0, reason, fg)
