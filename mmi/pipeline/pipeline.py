"""End-to-end orchestrator: .mp4 -> mmi-lite Scene .json.

    ingest -> keyframes -> reconstruct -> segment -> track -> assemble

Each stage is a thin module under ``mmi/stages``. Stages that need a GPU raise
NotImplementedError with a pointer to docs/ROADMAP.md; the ``synthetic`` recon
backend lets the whole chain (and the viewer) run today without one.
"""

from __future__ import annotations

import time

from mmi.formats.mmi_scene import Scene
from mmi.pipeline.config import PipelineConfig
from mmi.stages import assemble, ingest, keyframes, reconstruct, segment, track


def run(cfg: PipelineConfig, verbose: bool = True) -> Scene:
    def log(msg: str) -> None:
        if verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    log(f"1/6 ingest        : {cfg.video}")
    ing = ingest.run(cfg)
    log(f"      -> {len(ing.frame_paths)} frames @ ~{ing.sampled_fps:.1f} fps")

    log("2/6 keyframes     : selecting")
    kf = keyframes.run(cfg, ing)
    log(f"      -> {len(kf.keyframe_paths)} keyframes")

    log(f"3/6 reconstruct   : backend={cfg.recon_backend}")
    rec = reconstruct.run(cfg, kf)
    log(f"      -> {len(rec.slices)} time slices (backend={rec.backend})")

    log(f"4/6 segment       : {cfg.segmenter}")
    seg = segment.run(cfg, rec)
    log(f"      -> {len(seg.layer_names)} parts")

    log(f"5/6 track         : {cfg.track_method}")
    trk = track.run(cfg, rec, seg)
    log(f"      -> {len(trk.parts)} part tracks")

    log("6/6 assemble      : building mmi-lite scene")
    scene = assemble.run(cfg, rec, seg, trk, fps=max(1, round(ing.sampled_fps)))
    problems = scene.validate()
    if problems:
        log(f"  ! validation warnings: {problems}")
    scene.save(cfg.out_scene)
    log(f"done -> {cfg.out_scene}")
    return scene
