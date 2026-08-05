"""CV vision module — deterministic frame analysis, no vision LLM.

This module replaces the Gemini vision model with pure OpenCV operations.
Instead of sending frames to an LLM and asking "what do you see?", we run
optical flow, edge detection, color segmentation, and contour finding
directly. The results are structured numeric data the reasoning model
interprets.

Architecture: ONE reasoning model (DeepSeek) orchestrating many tools.
The CV modules here are tools — they extract raw visual features.
The reasoning model decides what they mean and how to build the 3D scene.
"""

from mmi.etu.vision.analysis import (
    ColorCluster,
    DetectedObject,
    FrameAnalysis,
    MotionRegion,
    analyze,
    dominant_colors,
    edge_density,
    edge_map,
    find_objects,
    motion_regions,
    optical_flow,
)
from mmi.etu.vision.extract import feature_graph_from_analysis

__all__ = [
    "FrameAnalysis", "MotionRegion", "ColorCluster", "DetectedObject",
    "analyze", "optical_flow", "motion_regions", "dominant_colors",
    "edge_map", "edge_density", "find_objects",
    "feature_graph_from_analysis",
]
