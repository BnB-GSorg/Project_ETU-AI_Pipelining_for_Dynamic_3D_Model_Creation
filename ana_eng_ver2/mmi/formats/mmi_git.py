"""mmi-git format — git-like delta storage for 4D processes.

A .mmi file contains:
  base:     full point cloud at frame 0, segmented into parts
  commits:  chronological list of whole-scene transforms (one 4×4 per part per commit)
  keyframes: periodic full snapshots for O(1) random access (every ~30 frames)

To render frame N: start from nearest keyframe ≤ N, apply commits
(keyframe_t+1..N). Each commit encodes a 4×4 homogeneous transform matrix
(rotation + translation + scale) per tracked part.

Design principle: like git, every change is a delta. Unlike git's line-based
diffs, these deltas are spatial — matrix multiplications. Just as git stores
the initial version + a chain of patches, this format stores the base point
cloud + a chain of 4×4 transforms.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

FORMAT_NAME = "mmi-git"
FORMAT_VERSION = "0.2"
KEYFRAME_INTERVAL = 30  # frames between periodic full snapshots


@dataclass
class GitGeometry:
    """Self-contained geometry for a part — box, line, surface, or pointcloud.

    For pointcloud: ``point_indices`` on PartSpec references the global base_points;
    the geometry dict only carries ``point_size``.
    For box/line/surface: the geometry data is self-contained and does NOT
    reference base_points — the commit-chain transforms apply to the mesh
    as a whole (position/quaternion/scale), not per-vertex.
    """

    kind: str  # "pointcloud" | "box" | "surface" | "line"
    point_size: float = 0.03          # pointcloud only
    size: list[float] | None = None   # box only: [sx, sy, sz]
    face_colors: dict[str, str] | None = None  # box only: {"px":"#rrggbb", ...}
    rows: int | None = None           # surface only
    cols: int | None = None           # surface only
    positions: list[float] | None = None  # surface / line: flat [x,y,z,...]
    surface_colors: list[float] | None = None  # surface per-vertex colors
    surface_color: str | None = None  # surface / line uniform color
    opacity: float = 1.0              # surface
    wireframe: bool = False           # surface
    line_width: float = 2.0           # line only

    def to_dict(self) -> dict[str, Any]:
        """Serialize this geometry to a JSON-safe dict."""
        d: dict[str, Any] = {"kind": self.kind}
        if self.kind == "pointcloud":
            d["point_size"] = self.point_size
        elif self.kind == "box":
            d["size"] = self.size
            d["face_colors"] = self.face_colors
        elif self.kind == "surface":
            d["rows"] = self.rows
            d["cols"] = self.cols
            if self.positions is not None:
                d["positions"] = [round(v, 4) for v in self.positions]
            if self.surface_colors is not None:
                d["colors"] = [round(v, 3) for v in self.surface_colors]
            if self.surface_color is not None:
                d["color"] = self.surface_color
            d["opacity"] = self.opacity
            d["wireframe"] = self.wireframe
        elif self.kind == "line":
            if self.positions is not None:
                d["positions"] = [round(v, 5) for v in self.positions]
            if self.surface_color is not None:
                d["color"] = self.surface_color
            d["width"] = self.line_width
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "GitGeometry":
        """Deserialize a GitGeometry from a JSON-safe dict."""
        kind = str(d["kind"])
        return GitGeometry(
            kind=kind,
            point_size=float(d.get("point_size", 0.03)),
            size=([float(v) for v in d["size"]] if d.get("size") else None),
            face_colors={str(k): str(v) for k, v in d["face_colors"].items()} if d.get("face_colors") else None,
            rows=int(d["rows"]) if d.get("rows") else None,
            cols=int(d["cols"]) if d.get("cols") else None,
            positions=([float(v) for v in d["positions"]] if d.get("positions") else None),
            surface_colors=([float(v) for v in d["colors"]] if d.get("colors") else None),
            surface_color=str(d["color"]) if d.get("color") else None,
            opacity=float(d.get("opacity", 1.0)),
            wireframe=bool(d.get("wireframe", False)),
            line_width=float(d.get("width", 2.0)),
        )


@dataclass
class PartSpec:
    """One segmented part of the scene.

    For pointcloud parts: ``point_indices`` references into the flat
    ``base_points`` array (every 3 floats = one point), and ``geometry``
    carries ``kind: pointcloud`` with an optional ``point_size``.

    For box / line / surface parts: ``point_indices`` is empty (or absent);
    ``geometry`` is self-contained and does NOT reference base_points.
    The commit-chain transforms apply to the mesh as a whole, keeping
    geometry crisp.
    """

    id: str
    label: str
    point_indices: list[int] = field(default_factory=list)
    geometry: GitGeometry | None = None
    color: str = "#8ab4ff"

    @property
    def geom_kind(self) -> str:
        if self.geometry is not None:
            return self.geometry.kind
        return "pointcloud"

    def to_dict(self) -> dict[str, Any]:
        """Serialize this part spec to a JSON-safe dict."""
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "color": self.color,
        }
        if self.geometry is not None:
            d["geometry"] = self.geometry.to_dict()
        if self.point_indices:
            d["point_indices"] = self.point_indices
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PartSpec":
        """Deserialize a PartSpec from a JSON-safe dict."""
        geom = GitGeometry.from_dict(d["geometry"]) if d.get("geometry") else None
        return PartSpec(
            str(d["id"]),
            str(d["label"]),
            [int(i) for i in d.get("point_indices", [])],
            geom,
            str(d.get("color", "#8ab4ff")),
        )


@dataclass
class Commit:
    """One frame's transforms for all tracked parts.

    ``transforms`` maps part_id → 16 floats (4×4 homogeneous matrix, row-major).
    The matrix encodes the delta from the previous frame to this one.
    To apply: P' = T @ [x, y, z, 1]^T → take first 3 components.

    ``t`` is the target frame index this commit moves TO.
    """

    t: int
    transforms: dict[str, list[float]]  # part_id → [m00..m33] (16 floats, row-major)

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "transforms": self.transforms}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Commit":
        return Commit(int(d["t"]), {str(k): [float(v) for v in vs] for k, vs in d["transforms"].items()})

    def matrix_for(self, part_id: str) -> np.ndarray | None:
        flat = self.transforms.get(part_id)
        if flat is None:
            return None
        return np.array(flat, dtype=np.float64).reshape(4, 4)

    def has_part(self, part_id: str) -> bool:
        return part_id in self.transforms


@dataclass
class KeyFrame:
    """Periodic full snapshot for O(1) random access.

    Instead of replaying the entire commit chain from frame 0 every time
    the user scrubs to frame 500, we store a full point-cloud snapshot
    every ~30 frames. This bounds seek cost to O(KEYFRAME_INTERVAL).
    """

    t: int
    parts: dict[str, list[float]]  # part_id → flat [x0,y0,z0, x1,y1,z1, ...] (world-space)

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "parts": self.parts}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "KeyFrame":
        return KeyFrame(int(d["t"]), {str(k): [float(v) for v in vs] for k, vs in d["parts"].items()})


@dataclass
class MmiGitScene:
    """Root container for the mmi-git format.

    Example construction and playback::

        scene = MmiGitScene(
            title="Collision demo", fps=12, duration_frames=120,
            base_points=[0,0,0, 5,0,0, ...],
            base_colors=[1,0,0, 0,0,1, ...],
            parts=[PartSpec("blue_ball", "Blue ball", [0,1,2])],
            commits=[
                Commit(0, {"blue_ball": [1,0,0,0.1, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
                Commit(1, {"blue_ball": [1,0,0,0.2, 0,1,0,0, 0,0,1,0, 0,0,0,1]}),
            ],
        )
        frame_1 = scene.compute_frame(1)  # → {"blue_ball": [0.3, 0, 0, 5.3, 0, 0, ...]}
    """

    title: str
    fps: int
    duration_frames: int

    # --- Base geometry (frame 0) ---
    base_points: list[float]  # flat [x0,y0,z0, x1,y1,z1, ...]
    base_colors: list[float] | None = None  # flat [r,g,b, r,g,b, ...] in 0..1

    # --- Segmentation ---
    parts: list[PartSpec] = field(default_factory=list)

    # --- Commit chain ---
    commits: list[Commit] = field(default_factory=list)

    # --- Periodic snapshots ---
    keyframes: list[KeyFrame] = field(default_factory=list)

    # --- Metadata ---
    layers: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    source: str = "reconstruction"
    coordinate_system: str = "right-handed-y-up"

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full scene to a JSON-safe dict."""
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "meta": {
                "title": self.title,
                "fps": self.fps,
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
    def from_dict(d: dict[str, Any]) -> "MmiGitScene":
        """Deserialize an MmiGitScene from a JSON-safe dict."""
        meta = d["meta"]
        base = d["base"]
        return MmiGitScene(
            title=str(meta["title"]),
            fps=int(meta["fps"]),
            duration_frames=int(meta["duration_frames"]),
            base_points=[float(v) for v in base["points"]],
            base_colors=([float(v) for v in base["colors"]] if base.get("colors") else None),
            parts=[PartSpec.from_dict(p) for p in d.get("parts", [])],
            commits=[Commit.from_dict(c) for c in d.get("commits", [])],
            keyframes=[KeyFrame.from_dict(k) for k in d.get("keyframes", [])],
            layers=list(d.get("layers", [])),
            events=list(meta.get("events", [])),
            source=str(meta.get("source", "reconstruction")),
            coordinate_system=str(meta.get("coordinate_system", "right-handed-y-up")),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    @staticmethod
    def load(path: str | Path) -> "MmiGitScene":
        return MmiGitScene.from_dict(json.loads(Path(path).read_text()))

    # ── Playback / random access ────────────────────────────────────────

    def nearest_keyframe(self, frame: int) -> tuple[int, KeyFrame | None]:
        """Find the closest keyframe snapshot at or before ``frame``.

        Returns (keyframe_t, KeyFrame) or (-1, None) if no keyframe qualifies.
        """
        best_t, best_kf = -1, None
        for kf in self.keyframes:
            if kf.t <= frame and kf.t > best_t:
                best_t, best_kf = kf.t, kf
        return best_t, best_kf

    def _base_points_for_part(self, part: PartSpec) -> np.ndarray:
        """Extract the (N,3) base points that belong to a pointcloud part.

        Returns empty (0,3) array for non-pointcloud parts.
        """
        if part.geom_kind != "pointcloud":
            return np.zeros((0, 3), dtype=np.float64)
        if not part.point_indices:
            return np.zeros((0, 3), dtype=np.float64)
        all_pts = np.array(self.base_points, dtype=np.float64).reshape(-1, 3)
        indices = np.array(part.point_indices, dtype=int)
        return all_pts[indices].copy()

    def compute_frame(self, frame: int) -> dict[str, list[float]]:
        """Resolve part positions at frame ``frame`` by applying the commit chain.

        Algorithm:
          1. Find nearest keyframe at or before ``frame``.
          2. Initialize per-part positions from that keyframe (or the base).
          3. Apply commits with t in (keyframe_t, frame], in order.
          4. Return {part_id: [x0,y0,z0, x1,y1,z1, ...]} (flat list, world-space).

        Complexity: O(KEYFRAME_INTERVAL * num_parts * points_per_part).
        """
        start_t, kf = self.nearest_keyframe(frame)

        # ── Initialize from nearest keyframe or base ──
        current: dict[str, np.ndarray] = {}
        if kf is not None:
            for pid, flat_pos in kf.parts.items():
                current[pid] = np.array(flat_pos, dtype=np.float64).reshape(-1, 3)
        else:
            for part in self.parts:
                current[part.id] = self._base_points_for_part(part)

        # Also ensure any part in commits that wasn't in base has a fallback
        for c in self.commits:
            for pid in c.transforms:
                if pid not in current:
                    # Part appeared mid-process — create empty placeholder
                    current[pid] = np.zeros((0, 3), dtype=np.float64)

        # ── Sort commits by t ──
        sorted_commits = sorted(self.commits, key=lambda c: c.t)

        # ── Accumulate transforms ──
        for commit in sorted_commits:
            if commit.t <= start_t:
                continue
            if commit.t > frame:
                break

            for pid, T_flat in commit.transforms.items():
                if pid not in current:
                    continue
                pts = current[pid]
                if pts.shape[0] == 0:
                    continue
                T = np.array(T_flat, dtype=np.float64).reshape(4, 4)
                # Apply transform: (N,3) → homogeneous (N,4) → T @ (N,4)^T → (N,3)
                ones = np.ones((pts.shape[0], 1), dtype=np.float64)
                homogeneous = np.hstack([pts, ones])
                transformed = (T @ homogeneous.T).T[:, :3]
                current[pid] = transformed

        # ── Flatten to dict of flat lists ──
        return {pid: arr.flatten().tolist() for pid, arr in current.items()}

    def generate_keyframes(self, interval: int = KEYFRAME_INTERVAL) -> list[KeyFrame]:
        """Pre-compute periodic full snapshots for O(1) random access.

        Call this after building the commit chain (e.g. from the encoder).
        Returns the list; also stores them on ``self.keyframes``.
        """
        kfs = []
        for t in range(0, self.duration_frames, interval):
            frame_data = self.compute_frame(t)
            kfs.append(KeyFrame(t=t, parts=frame_data))
        self.keyframes = kfs
        return kfs

    # ── Inspection ──────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return human-readable problems; empty list means valid."""
        problems: list[str] = []

        if self.base_points is None:
            self.base_points = []
        if not isinstance(self.base_points, list):
            problems.append("base_points is not a list")

        if self.base_colors is not None and not isinstance(self.base_colors, list):
            problems.append("base_colors is not a list")

        part_ids = {p.id for p in self.parts}
        total_indices = sum(len(p.point_indices) for p in self.parts)
        n_base_points = len(self.base_points) // 3 if self.base_points else 0
        if total_indices > n_base_points:
            problems.append(f"part indices reference {total_indices} points but base has {n_base_points}")

        valid_kinds = {"pointcloud", "box", "surface", "line"}
        for p in self.parts:
            if p.geometry is not None and p.geometry.kind not in valid_kinds:
                problems.append(f"part {p.id!r} has unknown geometry kind {p.geometry.kind!r}")

        for c in self.commits:
            if c.t < 0 or c.t >= self.duration_frames:
                problems.append(f"commit t={c.t} out of range [0, {self.duration_frames})")
            for pid in c.transforms:
                if pid not in part_ids:
                    problems.append(f"commit t={c.t} references unknown part {pid!r}")
                if len(c.transforms[pid]) != 16:
                    problems.append(f"commit t={c.t} part {pid!r} has {len(c.transforms[pid])} values, expected 16")

        for kf in self.keyframes:
            if kf.t < 0 or kf.t >= self.duration_frames:
                problems.append(f"keyframe t={kf.t} out of range")
            for pid in kf.parts:
                if pid not in part_ids:
                    problems.append(f"keyframe t={kf.t} references unknown part {pid!r}")

        return problems

    @property
    def commit_count(self) -> int:
        return len(self.commits)

    @property
    def keyframe_count(self) -> int:
        return len(self.keyframes)

    @property
    def part_count(self) -> int:
        return len(self.parts)

    @property
    def total_points(self) -> int:
        return len(self.base_points) // 3


# ── Helpers ─────────────────────────────────────────────────────────────

def _round(values: list[float] | None, ndigits: int = 4) -> list[float] | None:
    if values is None:
        return None
    return [round(float(v), ndigits) for v in values]


def identity_matrix() -> list[float]:
    """Return a 4×4 identity matrix as a flat list (row-major)."""
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def translation_matrix(tx: float, ty: float, tz: float) -> list[float]:
    """Return a 4×4 pure-translation matrix as a flat list."""
    return [
        1.0, 0.0, 0.0, tx,
        0.0, 1.0, 0.0, ty,
        0.0, 0.0, 1.0, tz,
        0.0, 0.0, 0.0, 1.0,
    ]
