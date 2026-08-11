"""FeatureGraph extraction from CV analysis — no vision LLM needed.

Given FrameAnalysis (deterministic CV output), build a FeatureGraph.
Objects are tracked across frames by spatial overlap; shapes come from
contour classification; colors from the detected region's average.

The reasoning model then interprets this raw FeatureGraph — deciding what
the objects ARE (labels), whether a template matches, and how to author
the 3D scene. The CV job ends here: raw structured data, no semantics.
"""

from __future__ import annotations

from mmi.etu.understand.schema import FeatureGraph, FeatureObject, State
from mmi.etu.vision.analysis import DetectedObject, FrameAnalysis
from mmi.etu.understand.identity import reconcile


def _overlap(a: DetectedObject, b: DetectedObject) -> float:
    x_min = max(a.x - a.w / 2, b.x - b.w / 2)
    x_max = min(a.x + a.w / 2, b.x + b.w / 2)
    y_min = max(a.y - a.h / 2, b.y - b.h / 2)
    y_max = min(a.y + a.h / 2, b.y + b.h / 2)
    if x_min >= x_max or y_min >= y_max:
        return 0.0
    intersection = (x_max - x_min) * (y_max - y_min)
    union = a.w * a.h + b.w * b.h - intersection
    return intersection / union if union > 0 else 0.0


def feature_graph_from_analysis(
    analysis: FrameAnalysis,
    fps: int = 12,
    min_overlap: float = 0.15,
) -> FeatureGraph:
    """Build a FeatureGraph from deterministic CV frame analysis.
    
    Tracks objects across frames via overlap matching. Objects that appear
    in consecutive frames with sufficient spatial overlap are treated as
    the same object (same ID). Objects that appear/disappear get separate IDs.
    
    The resulting FeatureGraph has object IDs and raw features but NO
    semantic labels — that's for the reasoning model to fill in.
    """
    if analysis.n_frames == 0:
        return FeatureGraph(fps=fps)
    
    # Track objects across frames via spatial overlap matching
    tracked: list[list[dict]] = []  # tracked[i] = list of {id, obj} for frame i
    next_id = 0
    active_ids: dict[int, str] = {}  # track_id -> label prefix
    
    for fi, frame_objs in enumerate(analysis.objects_by_frame):
        frame_tracked = []
        matched_prev = set()
        
        for obj in frame_objs:
            best_overlap = 0.0
            best_id = None
            
            # Match against previous frame's objects by overlap
            if fi > 0:
                for prev in tracked[fi - 1]:
                    ov = _overlap(obj, prev["obj"])
                    if ov > best_overlap and prev["id"] not in matched_prev:
                        best_overlap = ov
                        best_id = prev["id"]
            
            if best_overlap >= min_overlap and best_id is not None:
                track_id = best_id
                matched_prev.add(best_id)
            else:
                track_id = f"obj_{next_id:02d}"
                active_ids[next_id] = obj.shape
                next_id += 1
            
            frame_tracked.append({"id": track_id, "obj": obj})
        
        tracked.append(frame_tracked)
    
    # Build FeatureGraph: collect timeline per tracked object
    obj_states: dict[str, list[dict]] = {}
    obj_shape: dict[str, str] = {}
    obj_color: dict[str, str] = {}
    obj_depth: dict[str, float] = {}
    
    for fi, frame_tracked in enumerate(tracked):
        for entry in frame_tracked:
            tid = entry["id"]
            do = entry["obj"]
            if tid not in obj_states:
                obj_states[tid] = []
                obj_shape[tid] = do.shape
                obj_color[tid] = do.color
                # Depth heuristic: bigger objects assumed closer
                obj_depth[tid] = max(0.0, min(1.0, 1.0 - do.w * do.h * 3))
            obj_states[tid].append({
                "t": fi, "x": do.x, "y": do.y,
                "size": max(do.w, do.h),
                "opacity": 1.0,
            })
    
    # Sort by first appearance for deterministic ordering
    sorted_ids = sorted(obj_states.keys(), key=lambda tid: obj_states[tid][0]["t"])
    
    objects = []
    for tid in sorted_ids:
        states = obj_states[tid]
        objects.append(FeatureObject(
            id=tid,
            label="",  # Reasoning model fills this in
            shape=obj_shape.get(tid, "blob"),
            color=obj_color.get(tid, "#8ab4ff"),
            depth=obj_depth.get(tid, 0.5),
            timeline=[State(**s) for s in states],
        ))
    
    fg = FeatureGraph(
        summary="",  # Reasoning model fills this in
        fps=fps,
        duration=analysis.n_frames,
        objects=objects,
    )
    
    # Run identity reconciliation to merge any split IDs
    reconcile(fg)
    
    return fg
