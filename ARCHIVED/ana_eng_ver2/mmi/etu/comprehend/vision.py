"""DEPRECATED — Vision "eye" via Gemini LLM.

This module is kept for backward compatibility but is NO LONGER the primary
vision path. The single-model architecture uses deterministic CV modules
(mmi/etu/vision/) instead — optical flow, edge detection, contour finding,
color segmentation. Those modules are free, fast, and require no API keys.

This file remains so existing code that imports describe_frames doesn't break,
but new code should use mmi.etu.vision.analyze() instead.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mmi.etu.comprehend.llm import LLMConfig, make_config, vision_chat

VISION_SYSTEM = """You are a precise visual describer for math and science \
explainer videos. You are shown frames sampled in time order from one short clip.

Describe ONLY what is visually present and relevant to identifying the underlying \
concept, in plain prose:
- any equations, formulas or symbols shown (transcribe them exactly if legible);
- axes and their labels, ranges, gridlines;
- the kind of visual: 2D curve, heatmap/color field, 3D surface, waveform, vectors, geometry;
- notable colors or color schemes (e.g. a hue wheel / domain coloring);
- what CHANGES across the frames (the animation): what moves, grows, morphs, or accumulates.

Do NOT name or guess the topic, and do NOT mention any visualization template. \
Just report what is on screen, factually and concisely."""


def _sample(frames: list[Path], k: int) -> list[Path]:
    if len(frames) <= k:
        return frames
    step = (len(frames) - 1) / (k - 1)
    return [frames[round(i * step)] for i in range(k)]


def describe_frames(
    frames: list[Path],
    cfg: LLMConfig | None = None,
    chat_fn: Callable[[str, str, list[str]], str] | None = None,
    hint: str = "",
    max_images: int = 6,
) -> str:
    """Return a factual text description of the frames (the 'eye' output)."""
    if not frames:
        return ""
    picked = _sample(list(frames), max_images)
    user = (f"Context hint: {hint}\n\n" if hint else "") + \
        f"Describe these {len(picked)} frames, sampled in time order."

    if chat_fn is None:
        cfg = cfg or make_config("gemini")
        chat_fn = lambda s, u, imgs: vision_chat(cfg, s, u, imgs)  # noqa: E731

    return chat_fn(VISION_SYSTEM, user, [str(p) for p in picked]).strip()
