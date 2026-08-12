"""Stage 6 — Assemble: merge reconstruction + segmentation + tracking into one
temporally-coherent mmi-lite Scene (the viewer/Person-B handoff artifact).

For each segmented part we emit one SceneObject whose static geometry is its
point cloud (in a canonical/reference frame) and whose track is the per-time
rigid pose recovered by the tracking stage.
"""

from __future__ import annotations

import numpy as np

from mmi.formats.mmi_scene import (
    Keyframe,
    Layer,
    PointCloudGeometry,
    Scene,
    SceneObject,
)
from mmi.pipeline.config import PipelineConfig
from mmi.stages.reconstruct import Reconstruction
from mmi.stages.segment import Segmentation
from mmi.stages.track import Tracking

_PALETTE = ["#5b8cff", "#ff6b6b", "#51cf66", "#ffd43b", "#cc5de8", "#22b8cf", "#ff922b", "#94d82d"]


def run(
    cfg: PipelineConfig,
    recon: Reconstruction,
    seg: Segmentation,
    tracking: Tracking,
    fps: int = 4,
) -> Scene:
    if not recon.slices:
        raise ValueError("empty reconstruction — nothing to assemble")

    duration = max(sl.t for sl in recon.slices) + 1
    ref = recon.slices[0]
    layers = [
        Layer(f"part_{pid}", seg.layer_names.get(pid, f"part_{pid}"), _PALETTE[i % len(_PALETTE)])
        for i, pid in enumerate(sorted(seg.layer_names) or [0])
    ]

    objects: list[SceneObject] = []
    for pt in tracking.parts:
        mask = seg.labels[0] == pt.part_id if seg.labels else np.ones(len(ref.points), bool)
        pts = ref.points[mask]
        cols = ref.colors[mask] if ref.colors is not None else None
        if len(pts) == 0:
            continue
        # center geometry so the track's position carries world placement
        centroid = pts.mean(0)
        geom = PointCloudGeometry(
            points=(pts - centroid).flatten().tolist(),
            colors=cols.flatten().tolist() if cols is not None else None,
            point_size=0.03,
        )
        track = [
            Keyframe(kf["t"], kf["position"], kf["quaternion"]) for kf in pt.keyframes
        ] or [Keyframe(0, centroid.tolist())]
        objects.append(
            SceneObject(id=f"part_{pt.part_id:02d}", geometry=geom, track=track, layer=f"part_{pt.part_id}")
        )

    return Scene(
        title=f"Reconstructed process ({recon.backend})",
        fps=fps,
        duration_frames=duration,
        objects=objects,
        layers=layers,
        source=f"video:{recon.backend}",
    )
