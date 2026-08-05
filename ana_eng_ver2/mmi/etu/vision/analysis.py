"""Deterministic CV analysis — the "eyes" that replace the vision LLM.

Instead of sending frames to Gemini and asking "what do you see?", we run
deterministic computer vision operations directly on the frames. The results
are structured numeric data — motion vectors, edge maps, color clusters,
object contours — that the reasoning model can use as tools.

This module is the first half of the single-model architecture: CV extracts
raw features, the reasoning model interprets them.

All operations are local, free, and deterministic — no API keys, no network,
no LLM calls. This is the same class of CV tools the reconstruction pipeline
uses (optical flow in tracking, color clustering in segmentation).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ── low-level image I/O (PIL, cached) ────────────────────────────

def _gray(path: Path, size: int = 128) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert("L").resize((size, size)), dtype=np.float32)


def _rgb(path: Path, size: int = 128) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB").resize((size, size)), dtype=np.float32)


# ── optical flow / motion ────────────────────────────────────────

def optical_flow(frames: list[Path], size: int = 128) -> np.ndarray:
    """Dense optical flow magnitude per frame-transition (Farneback).
    
    Returns shape (len(frames)-1, size, size) — per-pixel motion magnitude.
    frame i → i+1 flow stored at index i.
    """
    try:
        import cv2
    except ImportError:
        raise RuntimeError("opencv-python required for CV vision module")
    
    if len(frames) < 2:
        return np.zeros((0, size, size), dtype=np.float32)
    
    flows = []
    prev = cv2.cvtColor(_rgb(frames[0], size).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    for fp in frames[1:]:
        curr = cv2.cvtColor(_rgb(fp, size).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev, curr, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        flows.append(mag)
        prev = curr
    return np.array(flows, dtype=np.float32)


def motion_regions(flow: np.ndarray, threshold: float = 0.5) -> list[MotionRegion]:
    """Find contiguous regions of significant motion from optical flow.
    
    Each region is a bounding box + centroid of pixels where motion > threshold.
    These are candidate "objects" — things that moved between frames.
    """
    if flow.size == 0:
        return []
    
    h, w = flow.shape
    binary = (flow > threshold).astype(np.uint8)
    
    # Simple connected-components without cv2 dependency for labeling
    # Use findContours via cv2
    try:
        import cv2
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except ImportError:
        # Fallback: grid-based region finding
        contours = _grid_regions(binary)
    
    regions = []
    for cnt in contours:
        if len(cnt) < 3:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt) if 'cv2' in dir() else _bbox(cnt)
        area = bw * bh
        if area < 4:  # skip noise
            continue
        cx = (x + bw / 2) / w   # normalized 0..1
        cy = (y + bh / 2) / h
        regions.append(MotionRegion(
            x=cx, y=cy, w=bw / w, h=bh / h,
            area=area, magnitude=float(np.mean(flow[y:y+bh, x:x+bw])),
        ))
    return regions


def _grid_regions(binary: np.ndarray) -> list[np.ndarray]:
    """Fallback region finding without cv2: simple grid-based blobs."""
    h, w = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    regions = []
    for y in range(h):
        for x in range(w):
            if binary[y, x] and not visited[y, x]:
                # flood fill
                stack = [(y, x)]
                blob = []
                while stack:
                    cy, cx = stack.pop()
                    if 0 <= cy < h and 0 <= cx < w and binary[cy, cx] and not visited[cy, cx]:
                        visited[cy, cx] = True
                        blob.append([cx, cy])
                        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                            stack.append((cy+dy, cx+dx))
                if len(blob) >= 4:
                    regions.append(np.array(blob, dtype=np.int32).reshape(-1, 1, 2))
    return regions


def _bbox(cnt: np.ndarray) -> tuple[int, int, int, int]:
    x = min(c[0][0] for c in cnt)
    y = min(c[0][1] for c in cnt)
    w = max(c[0][0] for c in cnt) - x + 1
    h = max(c[0][1] for c in cnt) - y + 1
    return x, y, w, h


@dataclass
class MotionRegion:
    x: float          # centroid x (0..1, normalized)
    y: float          # centroid y (0..1, normalized)
    w: float          # width (0..1)
    h: float          # height (0..1)
    area: float       # pixel area
    magnitude: float  # mean motion magnitude in region


# ── color segmentation ───────────────────────────────────────────

def dominant_colors(frame: Path, k: int = 5, size: int = 64) -> list[ColorCluster]:
    """K-means color clustering on a single frame.
    
    Returns the k dominant color clusters with their centroids (hex) and sizes.
    Use this to identify distinct-colored objects in a scene.
    """
    img = _rgb(frame, size).reshape(-1, 3)
    
    # Simple k-means (no sklearn dependency)
    centroids = img[np.random.choice(len(img), min(k, len(img)), replace=False)].astype(np.float32)
    for _ in range(10):
        # Assign
        dists = np.sum((img[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        labels = np.argmin(dists, axis=1)
        # Update
        new_centroids = np.array([img[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i] for i in range(k)], dtype=np.float32)
        if np.allclose(centroids, new_centroids, atol=0.5):
            break
        centroids = new_centroids
    
    clusters = []
    for i in range(k):
        count = int(np.sum(labels == i))
        if count < 5:  # skip tiny clusters
            continue
        r, g, b = centroids[i].astype(int)
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        clusters.append(ColorCluster(hex=hex_color, fraction=count / len(img)))
    
    clusters.sort(key=lambda c: c.fraction, reverse=True)
    return clusters


@dataclass
class ColorCluster:
    hex: str         # #rrggbb
    fraction: float  # 0..1, portion of image this color covers


# ── edge detection ───────────────────────────────────────────────

def edge_map(frame: Path, size: int = 128, low: float = 50, high: float = 150) -> np.ndarray:
    """Canny edge detection on a single frame.
    
    Returns binary edge map (size x size). Edges indicate boundaries —
    useful for detecting object shapes and counting distinct objects.
    """
    try:
        import cv2
    except ImportError:
        raise RuntimeError("opencv-python required for CV vision module")
    gray = _gray(frame, size).astype(np.uint8)
    return cv2.Canny(gray, low, high)


def edge_density(edges: np.ndarray) -> float:
    """Fraction of edge pixels — simple complexity measure."""
    return float(np.count_nonzero(edges)) / edges.size


# ── contour / object detection ───────────────────────────────────

def find_objects(frame: Path, size: int = 128,
                 min_area: int = 20) -> list[DetectedObject]:
    """Find distinct objects in a frame via contour detection.
    
    Uses edge detection + contour finding. Each contour is a candidate object.
    Returns list with position, size, and simple shape classification.
    """
    try:
        import cv2
    except ImportError:
        raise RuntimeError("opencv-python required for CV vision module")
    
    # Adaptive threshold for better object separation
    gray = _gray(frame, size).astype(np.uint8)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 11, 2)
    
    # Morphological close to join nearby fragments
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    h, w = size, size
    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        
        x, y, bw, bh = cv2.boundingRect(cnt)
        M = cv2.moments(cnt)
        cx = (M["m10"] / M["m00"]) / w if M["m00"] > 0 else (x + bw/2) / w
        cy = (M["m01"] / M["m00"]) / h if M["m00"] > 0 else (y + bh/2) / h
        
        # Shape classification
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        circularity = 4 * math.pi * area / (peri * peri) if peri > 0 else 0
        
        if circularity > 0.7:
            shape = "sphere"
        elif len(approx) <= 4:
            shape = "box"
        elif len(approx) <= 6:
            shape = "box"  # slightly rounded box
        else:
            shape = "blob"
        
        # Get dominant color for this object
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        rgb = _rgb(frame, size)
        masked = rgb[mask > 0]
        if len(masked) > 0:
            avg_color = masked.mean(axis=0).astype(int)
            color = f"#{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"
        else:
            color = "#8ab4ff"
        
        objects.append(DetectedObject(
            x=cx, y=cy, w=bw / w, h=bh / h,
            area=area, shape=shape, color=color,
        ))
    
    return objects


@dataclass
class DetectedObject:
    x: float      # centroid x (0..1, normalized)
    y: float      # centroid y (0..1, normalized)
    w: float      # width (0..1)
    h: float      # height (0..1)
    area: float   # pixel area
    shape: str    # "sphere", "box", "blob"
    color: str    # #rrggbb


# ── frame analysis summary ───────────────────────────────────────

@dataclass
class FrameAnalysis:
    """Structured CV analysis of a set of frames — the replacement for
    the vision LLM's text description. This is what the reasoning model
    receives as tool output."""
    n_frames: int
    size: tuple[int, int]  # analysis resolution
    motion: np.ndarray | None = None          # optical flow magnitude per transition
    motion_regions: list[list[MotionRegion]] = field(default_factory=list)  # per transition
    colors: list[ColorCluster] = field(default_factory=list)   # from first frame
    edge_fraction: float = 0.0                # mean edge density
    objects_by_frame: list[list[DetectedObject]] = field(default_factory=list)


def analyze(frames: list[Path], size: int = 128) -> FrameAnalysis:
    """Run all deterministic CV analysis on a set of frames.
    
    This is the single entry point: given frames, return structured visual data.
    The reasoning model then interprets this data to build a FeatureGraph.
    No LLM is called — this is pure OpenCV/numpy.
    """
    if not frames:
        return FrameAnalysis(n_frames=0, size=(size, size))
    
    # Motion
    motion = optical_flow(frames, size)
    mr_per_transition = [motion_regions(m) for m in motion] if motion.size > 0 else []

    # Colors from first frame
    colors = dominant_colors(frames[0], k=5, size=size)

    # Edge density (average across frames)
    edge_fracs = []
    for f in frames:
        edges = edge_map(f, size)
        edge_fracs.append(edge_density(edges))
    mean_edge = float(np.mean(edge_fracs)) if edge_fracs else 0.0

    # Objects per frame
    objects_by_frame = [find_objects(f, size) for f in frames]

    return FrameAnalysis(
        n_frames=len(frames),
        size=(size, size),
        motion=motion,
        motion_regions=mr_per_transition,
        colors=colors,
        edge_fraction=mean_edge,
        objects_by_frame=objects_by_frame,
    )
