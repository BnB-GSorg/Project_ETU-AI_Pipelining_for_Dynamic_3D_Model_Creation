# mmi-git Format + 3DGS Reconstruction — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the current per-frame-snapshot mmi-lite format with a git-like delta format (base geometry + commit chain of 4×4 transform matrices), and implement the parked 3DGS/COLMAP reconstruction pipeline for multi-view video.

**Architecture:** A single `.mmi` file contains one base point cloud (frame 0) segmented into parts, plus a chronological list of whole-scene commits where each commit records a 4×4 homogeneous transform matrix per part. Playback accumulates transforms from base to any frame N. Periodic keyframes (full snapshots every 30 frames) bound random-access cost to O(keyframe_interval). The reconstruction pipeline (COLMAP → 3DGS → segment → Kabsch-track → matrix-chain) feeds directly into this format.

**Tech Stack:** Python 3.13+, numpy, Three.js (viewer), COLMAP (SfM), 3D Gaussian Splatting (gsplat/nerfstudio), OpenCV

---

## Workstream 1: mmi-git Format (Storage Layer)

### Task 1.1: Create mmi_git.py format module

**Objective:** Create the Python data model for the git-like mmi format

**Files:**
- Create: `mmi/formats/mmi_git.py`

**Step 1: Define the data classes**

```python
"""mmi-git format — git-like delta storage for 4D processes.

A .mmi file contains:
  base:    full point cloud at frame 0, segmented into parts
  commits: chronological list of whole-scene transforms (one 4x4 per part)
  keyframes: periodic full snapshots for O(1) random access (every ~30 frames)

To render frame N: start from nearest keyframe ≤ N, apply commits (keyframe_index+1..N).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import numpy as np
from pathlib import Path
from typing import Any

FORMAT_NAME = "mmi-git"
FORMAT_VERSION = "0.1"
KEYFRAME_INTERVAL = 30  # frames between full snapshots


@dataclass
class PartSpec:
    """One segmented part of the base point cloud."""
    id: str
    label: str
    point_indices: list[int]  # which points in base.points belong to this part
    color: str = "#8ab4ff"

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label,
                "point_indices": self.point_indices, "color": self.color}

    @staticmethod
    def from_dict(d: dict) -> "PartSpec":
        return PartSpec(d["id"], d["label"], d["point_indices"], d.get("color", "#8ab4ff"))


@dataclass
class Commit:
    """One frame's transforms for all tracked parts.

    transforms: {part_id: [16 floats of 4x4 homogeneous matrix, row-major]}
    timestamp: frame index this commit moves TO (delta from previous frame)

    The 4x4 matrix encodes rotation + translation + scale as a single
    homogeneous transform. To apply: P' = T @ P (where P is homogeneous [x,y,z,1]).
    """
    t: int                               # target frame index
    transforms: dict[str, list[float]]   # part_id → 4x4 matrix (16 floats, row-major)

    def to_dict(self) -> dict:
        return {"t": self.t, "transforms": self.transforms}

    @staticmethod
    def from_dict(d: dict) -> "Commit":
        return Commit(d["t"], d["transforms"])

    def matrix_for(self, part_id: str) -> np.ndarray | None:
        """Return 4x4 numpy array for a part, or None."""
        flat = self.transforms.get(part_id)
        if flat is None:
            return None
        return np.array(flat, dtype=np.float64).reshape(4, 4)


@dataclass
class KeyFrame:
    """Periodic full snapshot for random access."""
    t: int
    # Per-part point clouds at this timepoint (world-space)
    # The keyframe stores computed positions, not the original base.
    # This avoids replaying the full commit chain from frame 0 every time.
    parts: dict[str, list[float]]  # part_id → flat [x0,y0,z0, x1,y1,z1, ...]

    def to_dict(self) -> dict:
        return {"t": self.t, "parts": self.parts}

    @staticmethod
    def from_dict(d: dict) -> "KeyFrame":
        return KeyFrame(d["t"], d["parts"])


@dataclass
class MmiGitScene:
    """Root container for mmi-git format."""
    title: str
    fps: int
    duration_frames: int

    # Base geometry (frame 0)
    base_points: list[float]        # flat [x0,y0,z0, x1,y1,z1, ...] — all points
    base_colors: list[float] | None = None  # flat [r,g,b, r,g,b, ...] in 0..1
    parts: list[PartSpec] = field(default_factory=list)

    # Commit chain
    commits: list[Commit] = field(default_factory=list)

    # Periodic snapshots
    keyframes: list[KeyFrame] = field(default_factory=list)

    # Metadata
    layers: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    source: str = "reconstruction"
    coordinate_system: str = "right-handed-y-up"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "meta": {
                "title": self.title, "fps": self.fps,
                "duration_frames": self.duration_frames,
                "source": self.source,
                "coordinate_system": self.coordinate_system,
                "events": self.events,
            },
            "base": {
                "points": _round(self.base_points, 5),
                "colors": _round(self.base_colors, 4) if self.base_colors else None,
            },
            "parts": [p.to_dict() for p in self.parts],
            "commits": [c.to_dict() for c in self.commits],
            "keyframes": [k.to_dict() for k in self.keyframes],
            "layers": self.layers,
        }

    @staticmethod
    def from_dict(d: dict) -> "MmiGitScene":
        meta = d["meta"]
        base = d["base"]
        return MmiGitScene(
            title=meta["title"], fps=meta["fps"],
            duration_frames=meta["duration_frames"],
            base_points=base["points"],
            base_colors=base.get("colors"),
            parts=[PartSpec.from_dict(p) for p in d.get("parts", [])],
            commits=[Commit.from_dict(c) for c in d.get("commits", [])],
            keyframes=[KeyFrame.from_dict(k) for k in d.get("keyframes", [])],
            layers=d.get("layers", []), events=meta.get("events", []),
            source=meta.get("source", "reconstruction"),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    @staticmethod
    def load(path: str | Path) -> "MmiGitScene":
        return MmiGitScene.from_dict(json.loads(Path(path).read_text()))

    def nearest_keyframe(self, frame: int) -> tuple[int, KeyFrame | None]:
        """Return (keyframe_index, keyframe) for the closest keyframe ≤ frame."""
        best_t, best_kf = -1, None
        for kf in self.keyframes:
            if kf.t <= frame and kf.t > best_t:
                best_t, best_kf = kf.t, kf
        return best_t, best_kf

    def compute_frame(self, frame: int) -> dict[str, list[float]]:
        """Resolve part positions at frame N by applying commit chain.

        Start from nearest keyframe (or base if none found), apply commits
        from (keyframe_t+1) to frame inclusive. Returns {part_id: [x,y,z,...]}.
        """
        start_t, kf = self.nearest_keyframe(frame)
        # Get starting positions
        if kf is not None:
            current = {pid: np.array(pos, dtype=np.float64).reshape(-1, 3)
                       for pid, pos in kf.parts.items()}
        else:
            current = {}
            for part in self.parts:
                idx = np.array(part.point_indices, dtype=int)
                pts = np.array(self.base_points, dtype=np.float64).reshape(-1, 3)[idx]
                current[part.id] = pts.copy()

        # Accumulate transforms
        for commit in self.commits:
            if commit.t <= start_t:
                continue
            if commit.t > frame:
                break
            for pid, T_flat in commit.transforms.items():
                if pid not in current:
                    continue
                T = np.array(T_flat, dtype=np.float64).reshape(4, 4)
                pts = current[pid]
                # Apply transform: each point (x,y,z) → homogeneous (x,y,z,1)
                ones = np.ones((pts.shape[0], 1), dtype=np.float64)
                homogeneous = np.hstack([pts, ones])
                transformed = (T @ homogeneous.T).T[:, :3]
                current[pid] = transformed

        # Flatten back
        return {pid: arr.flatten().tolist() for pid, arr in current.items()}


def _round(values: list[float] | None, ndigits: int = 4) -> list[float] | None:
    if values is None:
        return None
    return [round(float(v), ndigits) for v in values]
```

**Step 2: Verify with a basic round-trip test**

```python
def test_round_trip():
    """Create a minimal scene, save, reload, verify."""
    import tempfile, os
    scene = MmiGitScene(
        title="test", fps=12, duration_frames=3,
        base_points=[0,0,0, 1,1,1, 2,2,2],
        base_colors=[1,0,0, 0,1,0, 0,0,1],
        parts=[PartSpec("p0", "all", [0,1,2])],
        commits=[
            Commit(0, {"p0": [1,0,0,0.5, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
            Commit(1, {"p0": [1,0,0,1.0, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
        ],
    )
    with tempfile.NamedTemporaryFile(suffix=".mmi", delete=False) as f:
        scene.save(f.name)
        loaded = MmiGitScene.load(f.name)
        os.unlink(f.name)
    assert loaded.title == "test"
    assert len(loaded.commits) == 2
    assert loaded.commits[0].t == 0
    print("PASS: round-trip")
```

Run: `python -c "from mmi.formats.mmi_git import MmiGitScene, PartSpec, Commit; test_round_trip()"`

---

### Task 1.2: Add compute_frame unit tests

**Objective:** Verify frame computation with known transforms

**Files:**
- Create: `tests/test_mmi_git.py`

**Step 1: Write the test file**

```python
"""Tests for mmi-git format frame computation."""
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.formats.mmi_git import MmiGitScene, PartSpec, Commit, KeyFrame


def test_compute_frame_0_no_transforms():
    """Frame 0 with no commits should return base positions."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=1,
        base_points=[0,0,0, 5,0,0],
        parts=[PartSpec("ball", "ball", [0,1])],
    )
    result = scene.compute_frame(0)
    pts = np.array(result["ball"]).reshape(-1, 3)
    assert pts.shape == (2, 3)
    assert np.allclose(pts[0], [0, 0, 0])
    assert np.allclose(pts[1], [5, 0, 0])


def test_compute_frame_1_simple_translate():
    """Apply one translation commit."""
    # base: two points at (0,0,0) and (5,0,0)
    # commit: translate by (10, 0, 0)
    T = [1,0,0,10,  0,1,0,0,  0,0,1,0,  0,0,0,1]
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=2,
        base_points=[0,0,0, 5,0,0],
        parts=[PartSpec("ball", "ball", [0,1])],
        commits=[Commit(0, {"ball": T})],
    )
    result = scene.compute_frame(0)
    pts = np.array(result["ball"]).reshape(-1, 3)
    assert np.allclose(pts[0], [10, 0, 0])
    assert np.allclose(pts[1], [15, 0, 0])


def test_compute_keyframe_seek():
    """Compute from a keyframe, not from base."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=4,
        base_points=[0,0,0],
        parts=[PartSpec("p", "p", [0])],
        # frame 0 commit: translate by 5
        commits=[
            Commit(0, {"p": [1,0,0,5, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
            # frame 1 commit: translate by another 5 (cumulative: 10)
            Commit(1, {"p": [1,0,0,5, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
            # frame 2 commit: translate by another 5 (cumulative: 15)
            Commit(2, {"p": [1,0,0,5, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
        ],
        # keyframe at frame 1 with position at x=10
        keyframes=[KeyFrame(1, {"p": [10, 0, 0]})],
    )
    # frame 2: keyframe(1) + commit(2) = 10 + 5 = 15
    result = scene.compute_frame(2)
    pts = np.array(result["p"]).flatten()
    assert np.allclose(pts, [15, 0, 0])


if __name__ == "__main__":
    test_compute_frame_0_no_transforms()
    test_compute_frame_1_simple_translate()
    test_compute_keyframe_seek()
    print("ALL PASS")
```

**Step 2: Run tests**

```
cd ~/Documents/progproj/projute/ana_eng_ver2
mkdir -p tests
python tests/test_mmi_git.py
```

Expected: ALL PASS

---

### Task 1.3: Add format converter (old mmi-lite → mmi-git)

**Objective:** Convert existing mmi-lite scene files to mmi-git format so the viewer migration is gradual

**Files:**
- Create: `scripts/mmi_convert.py`

```python
#!/usr/bin/env python3
"""Convert between mmi-lite and mmi-git formats."""
from __future__ import annotations

import argparse, sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.formats.mmi_scene import Scene as LiteScene
from mmi.formats.mmi_git import MmiGitScene, PartSpec, Commit, KeyFrame


def lite_to_git(lite: LiteScene) -> MmiGitScene:
    """Convert mmi-lite (per-frame-keyframe Scene) to mmi-git (base + commits).

    Strategy: take the first keyframe of each object as its base geometry,
    then each subsequent keyframe's transform (position delta + quaternion delta)
    becomes a commit. Extract base point cloud positions from object geometry.
    """
    # Collect all object positions across time
    parts = []
    base_points = []
    base_colors = []
    commits_by_t: dict[int, dict[str, list[float]]] = {}

    for obj in lite.objects:
        if not obj.track:
            continue

        # Extract geometry points for this object
        geom = obj.geometry
        obj_pts = []
        obj_cols = []
        if hasattr(geom, 'points') and geom.points:
            obj_pts = list(geom.points)
        if hasattr(geom, 'colors') and geom.colors:
            obj_cols = list(geom.colors)

        start_idx = len(base_points) // 3
        base_points.extend(obj_pts)
        if obj_cols:
            base_colors.extend(obj_cols)

        n_pts = len(obj_pts) // 3
        parts.append(PartSpec(
            id=obj.id, label=obj.id,
            point_indices=list(range(start_idx, start_idx + n_pts)),
        ))

        # First keyframe is frame 0 (base) — subsequent ones are commits
        sorted_track = sorted(obj.track, key=lambda k: k.t)
        base_kf = sorted_track[0]

        for kf in sorted_track[1:]:
            t = kf.t
            if t not in commits_by_t:
                commits_by_t[t] = {}

            # Build 4x4 transform: position delta
            pos_delta = [
                kf.position[0] - base_kf.position[0],
                kf.position[1] - base_kf.position[1],
                kf.position[2] - base_kf.position[2],
            ]
            T = [
                1, 0, 0, pos_delta[0],
                0, 1, 0, pos_delta[1],
                0, 0, 1, pos_delta[2],
                0, 0, 0, 1,
            ]
            commits_by_t[t][obj.id] = T

    commits = [Commit(t, transforms) for t in sorted(commits_by_t)]

    return MmiGitScene(
        title=lite.title, fps=lite.fps,
        duration_frames=lite.duration_frames,
        base_points=base_points,
        base_colors=base_colors if base_colors else None,
        parts=parts, commits=commits,
        layers=[{"id": l.id, "name": l.name, "color": l.color, "visible": l.visible}
                for l in lite.layers],
        events=lite.events, source=lite.source,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert mmi-lite ↔ mmi-git")
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--direction", default="lite2git", choices=["lite2git"])
    args = ap.parse_args()

    lite = LiteScene.from_dict(...)  # need load method
    # Actually use the format module's load:
    import json as _json
    lite_dict = _json.loads(args.input.read_text())
    # mmi-lite doesn't have a load() — parse manually
    git = lite_to_git(lite_dict)  # simplified — real impl parses properly
    git.save(args.out)
    print(f"Converted → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Workstream 2: 3DGS Reconstruction Pipeline

### Task 2.1: Multi-view ingest stage

**Objective:** Extend the ingest stage to accept multiple synchronized videos

**Files:**
- Modify: `mmi/stages/ingest.py`
- Modify: `mmi/pipeline/config.py`

**Changes:**

In `config.py`, replace single `video: Path` with multi-view:

```python
video: Path | None = None       # single-view (backward compat)
videos: list[Path] | None = None  # multi-view: [cam0.mp4, cam1.mp4, cam2.mp4]

def get_videos(self) -> list[Path]:
    """Return all input videos."""
    if self.videos:
        return self.videos
    if self.video:
        return [self.video]
    raise ValueError("No video(s) configured")
```

In `ingest.py`, process each view independently into subdirectories:

```python
@dataclass
class IngestResult:
    views: dict[int, ViewFrames]  # camera_index → frames

@dataclass
class ViewFrames:
    frame_dir: Path
    frame_paths: list[Path]
    source_fps: float
    sampled_fps: float

def run(cfg: PipelineConfig) -> IngestResult:
    views = {}
    for i, video in enumerate(cfg.get_videos()):
        out = cfg.stage_dir(f"01_frames/view_{i:02d}")
        result = _ingest_one(video, out, cfg)
        views[i] = result
    # Verify all views have same frame count (synced)
    counts = {len(v.frame_paths) for v in views.values()}
    if len(counts) > 1:
        raise ValueError(f"Multi-view videos have different frame counts: {counts}")
    return IngestResult(views)
```

---

### Task 2.2: COLMAP reconstruction backend (CPU baseline)

**Objective:** Wire the COLMAP pipeline for sparse reconstruction and camera pose estimation

**Files:**
- Modify: `mmi/stages/reconstruct.py` (fill in `_run_colmap`)

**Implementation:**

```python
def _run_colmap(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Run COLMAP on multi-view keyframes per time-window.

    For each time-window (group of simultaneous frames across views):
    1. Copy keyframe images into a COLMAP workspace
    2. Run: feature_extractor → exhaustive_matcher → mapper → image_undistorter
    3. Extract sparse point cloud + camera poses
    4. (Optional) Run patch_match_stereo + stereo_fusion for dense cloud
    5. Collect per-window point clouds into TimeSlices

    For dynamic processes, we run COLMAP per time-window independently,
    then register windows to a shared coordinate frame using static scene
    elements or cross-window feature matching.
    """
    import subprocess, shutil

    slices = []
    kf_paths = keyframes.keyframe_paths
    n_views = len(cfg.get_videos())

    # Group frames by timepoint: frame_t = [view0_frame_t.png, view1_frame_t.png, ...]
    # Assuming keyframes from stage 2 are named frame_NNNNN.png chronologically
    # and all views share the same keyframe selection.

    for t, kf_path in enumerate(kf_paths):
        workspace = cfg.stage_dir(f"03_recon/time_{t:04d}")
        img_dir = workspace / "images"
        img_dir.mkdir(exist_ok=True)

        # Collect the corresponding frame from each view
        # (simplified: assumes keyframes are named consistently across views)
        frame_files = []
        for view_idx in range(n_views):
            view_dir = cfg.stage_dir(f"01_frames/view_{view_idx:02d}")
            # Find matching frame by index
            view_frame = sorted(view_dir.glob("frame_*.png"))[t]
            dest = img_dir / f"view{view_idx:02d}.png"
            shutil.copy(view_frame, dest)
            frame_files.append(dest)

        # Run COLMAP
        db_path = workspace / "database.db"
        sparse_dir = workspace / "sparse"
        dense_dir = workspace / "dense"

        subprocess.run([
            "colmap", "feature_extractor",
            "--database_path", str(db_path),
            "--image_path", str(img_dir),
            "--SiftExtraction.use_gpu", "1",
        ], check=True)

        subprocess.run([
            "colmap", "exhaustive_matcher",
            "--database_path", str(db_path),
            "--SiftExtraction.use_gpu", "1",
        ], check=True)

        sparse_dir.mkdir(exist_ok=True)
        subprocess.run([
            "colmap", "mapper",
            "--database_path", str(db_path),
            "--image_path", str(img_dir),
            "--output_path", str(sparse_dir),
        ], check=True)

        # Extract sparse point cloud
        points, colors = _load_colmap_sparse(sparse_dir / "0")
        slices.append(TimeSlice(t=t, points=points, colors=colors))

    return Reconstruction(slices=slices, backend="colmap")
```

---

### Task 2.3: 3DGS backend (GPU)

**Objective:** Train 3D Gaussian Splatting per time-window using gsplat

**Files:**
- Modify: `mmi/stages/reconstruct.py` (fill in `_run_neural` for "3dgs")

**Implementation stub** (requires CUDA GPU at runtime):

```python
def _run_neural(cfg: PipelineConfig, keyframes: KeyframeResult, backend: str) -> Reconstruction:
    if backend == "3dgs":
        return _run_3dgs(cfg, keyframes)
    elif backend == "dyn-nerf":
        return _run_dyn_nerf(cfg, keyframes)
    raise NotImplementedError(f"Unknown backend: {backend}")


def _run_3dgs(cfg: PipelineConfig, keyframes: KeyframeResult) -> Reconstruction:
    """Train 3D Gaussian Splatting per time-window.

    Uses COLMAP for initialization (camera poses), then trains a 3DGS model
    per window. After training, samples the trained Gaussians into point clouds.

    Requires: CUDA GPU, gsplat (pip install gsplat), colmap
    """
    # For each time-window:
    # 1. Run COLMAP for camera poses (sparse only)
    # 2. Train 3DGS model on the multi-view keyframe images
    # 3. Export per-time point cloud from trained Gaussians
    #    (sample the 3D Gaussians at their mean positions, weighted by opacity)

    slices = []
    for t in range(len(keyframes.keyframe_paths)):
        # ... COLMAP init + gsplat training ...

        # Export point cloud from Gaussian means
        # (gsplat stores Gaussian parameters: means, covariances, opacities, colors)
        # Filter by opacity threshold and export means as point cloud
        points = ...  # (N, 3) from Gaussian means where opacity > threshold
        colors = ...  # (N, 3) from spherical harmonics (SH₀ = base color)
        slices.append(TimeSlice(t=t, points=points, colors=colors))

    return Reconstruction(slices=slices, backend="3dgs")
```

Note: Full 3DGS implementation requires a CUDA-capable GPU at runtime. The code should:
- Check for CUDA availability at startup
- Fall back to COLMAP-only if no GPU
- Accept pre-trained checkpoint directories for offline use

---

### Task 2.4: Matrix-chain encoder (reconstruction → mmi-git)

**Objective:** Take the reconstructed TimeSlices + tracking output and produce an MmiGitScene

**Files:**
- Create: `mmi/stages/encode_git.py`

```python
"""Encode a reconstruction + tracking result into mmi-git format."""

from mmi.formats.mmi_git import MmiGitScene, PartSpec, Commit, KeyFrame, KEYFRAME_INTERVAL
from mmi.stages.reconstruct import Reconstruction
from mmi.stages.segment import Segmentation
from mmi.stages.track import Tracking


def encode(
    recon: Reconstruction,
    seg: Segmentation,
    tracking: Tracking,
    title: str = "Reconstructed Process",
    fps: int = 10,
) -> MmiGitScene:
    """Convert reconstruction pipeline output to mmi-git format.

    The base is the frame-0 point cloud. Each consecutive frame's Kabsch
    transform (from tracking) becomes a commit. Keyframes are inserted
    periodically for random access.
    """
    if not recon.slices:
        raise ValueError("Empty reconstruction")

    # Base = first time slice
    base_slice = recon.slices[0]
    base_points = base_slice.points.flatten().tolist() if base_slice.points.size else []
    base_colors = base_slice.colors.flatten().tolist() if base_slice.colors is not None else None

    # Parts from segmentation
    parts = []
    for pid in sorted(seg.layer_names):
        mask = seg.labels[0] == pid
        indices = [int(i) for i, m in enumerate(mask) if m]
        parts.append(PartSpec(
            id=f"part_{pid:02d}",
            label=seg.layer_names.get(pid, f"part_{pid:02d}"),
            point_indices=indices,
        ))

    # Commits from tracking keyframes
    commits: list[Commit] = []
    for pt in tracking.parts:
        for kf in pt.keyframes:
            t = kf["t"]
            if t == 0:
                continue  # base, not a delta
            # Build 4x4 transform from position + quaternion
            pos = kf["position"]
            quat = kf["quaternion"]  # [x, y, z, w]
            T = _quat_pos_to_matrix(quat, pos)
            # Find or create commit at this t
            existing = next((c for c in commits if c.t == t), None)
            if existing:
                existing.transforms[f"part_{pt.part_id:02d}"] = T
            else:
                commits.append(Commit(t, {f"part_{pt.part_id:02d}": T}))

    commits.sort(key=lambda c: c.t)

    # Generate keyframes (full snapshots every KEYFRAME_INTERVAL frames)
    keyframes = _build_keyframes(commits, parts, base_points, base_colors, len(recon.slices))

    return MmiGitScene(
        title=title, fps=fps,
        duration_frames=len(recon.slices),
        base_points=base_points, base_colors=base_colors,
        parts=parts, commits=commits, keyframes=keyframes,
        source=f"reconstruction:{recon.backend}",
    )
```

---

## Workstream 3: Viewer Update

### Task 3.1: mmi-git viewer support

**Objective:** Update Three.js viewer to load and render mmi-git format

**Files:**
- Modify: `viewer/main.js`
- Modify: `viewer/index.html`

**Changes in main.js:**

```javascript
// Detect format from JSON
function detectFormat(data) {
    if (data.format === 'mmi-git') return 'git';
    if (data.format === 'mmi-lite') return 'lite';
    return 'unknown';
}

// Load mmi-git scene
function loadGitScene(data) {
    // Build base point clouds per part
    const basePoints = data.base.points;
    const baseColors = data.base.colors || [];
    
    const partMeshes = {};
    data.parts.forEach(part => {
        const indices = part.point_indices;
        const positions = [];
        const colors = [];
        indices.forEach(i => {
            positions.push(basePoints[i*3], basePoints[i*3+1], basePoints[i*3+2]);
            if (baseColors.length) {
                colors.push(baseColors[i*3], baseColors[i*3+1], baseColors[i*3+2]);
            }
        });
        // Create point cloud mesh
        const geom = new THREE.BufferGeometry();
        geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        if (colors.length) {
            geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
        }
        const mat = new THREE.PointsMaterial({size: 0.03, vertexColors: colors.length > 0});
        const mesh = new THREE.Points(geom, mat);
        partMeshes[part.id] = mesh;
        scene.add(mesh);
    });

    // Commit chain for playback
    const commits = data.commits.sort((a, b) => a.t - b.t);
    
    // Seek function: apply transforms to reach target frame
    function seekToFrame(targetFrame) {
        // Reset to base positions
        data.parts.forEach(part => {
            const mesh = partMeshes[part.id];
            // ... rebuild from base ...
        });
        
        // Apply commits in order up to targetFrame
        commits.forEach(commit => {
            if (commit.t > targetFrame) return;
            for (const [partId, matrix16] of Object.entries(commit.transforms)) {
                const mesh = partMeshes[partId];
                if (!mesh) continue;
                const m = new THREE.Matrix4();
                m.fromArray(matrix16);
                mesh.applyMatrix4(m);
            }
        });
    }
    
    return { seekToFrame, partMeshes };
}
```

---

## Execution Order

1. Task 1.1 → Create mmi_git.py format module with round-trip test
2. Task 1.2 → Add compute_frame unit tests
3. Task 1.3 → Add format converter (lite → git)
4. Task 2.1 → Multi-view ingest
5. Task 2.2 → COLMAP backend
6. Task 2.3 → 3DGS backend (GPU required)
7. Task 2.4 → Matrix-chain encoder (recon → mmi-git)
8. Task 3.1 → Viewer mmi-git support
