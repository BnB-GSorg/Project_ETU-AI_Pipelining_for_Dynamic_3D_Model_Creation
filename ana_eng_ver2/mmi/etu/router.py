"""Router — the universal ETU entry point for any 2D animation.

ARCHITECTURE (single-model):
  Frames → CV analysis (deterministic, local) → FeatureGraph
         → Reasoning model (DeepSeek, the sole LLM) →
              ├─ template match → author correct template scene
              └─ no match → general lift from FeatureGraph

The vision LLM (Gemini) is GONE. CV modules (optical flow, edge detection,
contour finding, color segmentation) extract raw visual features from frames
deterministically — free, fast, no API keys. The reasoning model interprets
those features, labels objects, classifies the concept, and decides the
output path. One model, many tools.

Strategy:
  1. EXTRACT a FeatureGraph from frames via deterministic CV (no LLM).
  2. UPGRADE: if the reasoning model confidently matches a known template,
     author that template for a correct, high-quality lift.
  3. FALLBACK: otherwise lift the FeatureGraph generically — works on
     anything, honestly approximate on depth.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mmi.etu import synthesize
from mmi.etu.comprehend import comprehend
from mmi.etu.comprehend.llm import LLMConfig
from mmi.etu.guide import TransitionNote, apply_refinements, collect_guidance, guidance_text, refine
from mmi.etu.understand import FeatureGraph, extract, lift
from mmi.etu.understand.schema import FeatureGraph as FG
from mmi.formats.mmi_scene import Scene


@dataclass
class RouterResult:
    """Result of routing a 2D animation through the ETU pipeline."""
    scene: Scene | None
    method: str                 # "template" | "general" | "none"
    concept: str
    confidence: float
    rationale: str
    feature_graph: FeatureGraph | None
    notes: list[TransitionNote] = field(default_factory=list)  # human stage-change guidance


def comprehend_any(
    frames: list[Path] | None = None,
    transcript_text: str = "",
    hint: str = "",
    brain_cfg: LLMConfig | None = None,
    prefer: str = "auto",        # "auto" | "template" | "general"
    min_confidence: float = 0.55,
    chat_brain: Callable[[str, str], str] | None = None,
    fps: int = 12,
    max_cv_images: int = 8,
    interactive: bool = False,
    guide_prompt: Callable[[str], str | None] | None = None,
) -> RouterResult:
    """Route a 2D animation to the best 3D lift — single reasoning model only.

    NO vision LLM is used. FeatureGraph extraction is done by deterministic CV
    (optical flow + contour finding + color clustering). Only the reasoning
    model (DeepSeek) is called — for template classification and labeling.

    Args:
        frames: input frame paths (required for CV extraction)
        transcript_text: optional narration/transcript
        hint: optional context hint
        brain_cfg: reasoning model config (defaults to DeepSeek)
        prefer: "auto" | "template" | "general"
        min_confidence: threshold for template match
        chat_brain: reasoning model callable
        fps: frames per second for FeatureGraph
        max_cv_images: max frames for CV analysis
        interactive: if True, pause at each stage transition and ask the user to
            describe the change in natural language (empty = let the model guess)
        guide_prompt: prompt callback for interactive guidance (defaults to input())
    """
    fg: FeatureGraph | None = None
    if frames:
        # Deterministic CV extraction — NO vision LLM
        fg = extract(frames, fps=fps, max_images=max_cv_images, hint=hint)

    # Optional human-in-the-loop stage guidance (interactive only).
    notes: list[TransitionNote] = []
    if interactive and fg and fg.objects:
        notes = collect_guidance(fg, prompt=guide_prompt, interactive=True)
        if notes:
            # Fold the notes into the reasoning model and let it correct labels.
            # Best-effort: guidance must never break the automatic path.
            try:
                apply_refinements(fg, refine(fg, notes, cfg=brain_cfg, chat_fn=chat_brain))
            except Exception:
                pass

    # 1+2) try the closed-set template upgrade (reasoning model only)
    if prefer != "general":
        parts = [transcript_text, hint]
        if notes:
            parts.append("Human guidance on stage changes:\n" + guidance_text(notes))
        if fg:
            parts.append(fg.summary)
            parts += [o.label for o in fg.objects if o.label]
            # If CV found no labels, provide raw object info for the brain
            if not any(o.label for o in fg.objects):
                obj_desc = "; ".join(
                    f"{o.id}: {o.shape} at ({o.timeline[0].x:.2f},{o.timeline[0].y:.2f}) "
                    f"color={o.color}" if o.timeline else f"{o.id}: {o.shape} color={o.color}"
                    for o in fg.objects[:6]
                )
                if obj_desc:
                    parts.append(f"CV-detected objects: {obj_desc}")
        evidence = "\n".join(p for p in parts if p).strip()
        if evidence:
            c = comprehend(evidence, cfg=brain_cfg, chat_fn=chat_brain, min_confidence=min_confidence)
            if c.spec:
                return RouterResult(synthesize(c.spec), "template", c.concept, c.confidence, c.rationale, fg, notes)
            if prefer == "template":
                return RouterResult(None, "none", c.concept, c.confidence, c.rationale, fg, notes)

    # 3) general fallback — lift FeatureGraph directly
    if fg and not fg.validate():
        return RouterResult(lift(fg), "general", "general-lift", 1.0, "lifted FeatureGraph", fg, notes)

    reason = "no frames to extract from" if not fg else f"invalid FeatureGraph: {fg.validate()}"
    return RouterResult(None, "none", "none", 0.0, reason, fg)
