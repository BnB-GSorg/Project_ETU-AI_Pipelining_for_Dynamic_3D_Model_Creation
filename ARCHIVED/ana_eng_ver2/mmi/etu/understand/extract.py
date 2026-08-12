"""CV extractor: 2D animation frames -> FeatureGraph (domain-agnostic).

This is the REPLACEMENT for the old vision-LLM-based extractor. Instead of
sending frames to Gemini and asking it to describe objects, we run
deterministic CV operations (optical flow, edge detection, contour finding,
color segmentation) directly on the frames. The output is the same
FeatureGraph structure — but produced locally, for free, with no API calls.

The reasoning model (DeepSeek) then interprets this FeatureGraph, filling
in semantic labels, summaries, and deciding template vs general lift.

Architecture: frames → CV analysis → FeatureGraph → reasoning model → scene
            (no vision LLM anywhere in this pipeline)
"""

from __future__ import annotations

from pathlib import Path

from mmi.etu.understand.sampling import select_by_change
from mmi.etu.understand.schema import FeatureGraph


def extract(
    frames: list[Path],
    fps: int = 12,
    max_images: int = 8,
    hint: str = "",
) -> FeatureGraph:
    """Extract a FeatureGraph from frames using deterministic CV only.

    No vision LLM is called. The pipeline:
      1. Change-driven sampling: pick the frames where things actually move
      2. CV analysis: optical flow, edges, contours, colors on those frames
      3. Object tracking: follow blobs across frames via spatial overlap
      4. FeatureGraph: structured output ready for the reasoning model

    The returned FeatureGraph has object IDs and raw features but NO
    semantic labels — those are filled by the reasoning model in the router.
    """
    if not frames:
        return FeatureGraph(fps=fps)

    # Change-driven sampling: dense where animation moves, sparse where still
    picked = select_by_change(frames, max_images)

    # Lazy imports to avoid circular dependency (vision.extract → understand.schema)
    from mmi.etu.vision.analysis import analyze as cv_analyze
    from mmi.etu.vision.extract import feature_graph_from_analysis

    # Deterministic CV analysis — no API keys, no network, no LLM
    analysis = cv_analyze(picked)

    # Build FeatureGraph from tracked objects
    fg = feature_graph_from_analysis(analysis, fps=fps)

    # If a hint was provided, store it for the reasoning model
    if hint:
        fg.summary = f"[hint: {hint}]"

    return fg
