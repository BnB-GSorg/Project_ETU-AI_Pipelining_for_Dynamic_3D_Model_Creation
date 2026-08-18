"""mmi-git behavior: frame decoding, snapshots, validation.

Reimplements the 15 behaviors the archived engine's test_mmi_git.py checked,
adapted to the v0.3 model: commits carry whole poses (position, quaternion,
scale, opacity) instead of transforming raw point arrays directly, so a scene
that only rotates or fades is still representable and round-trips (archived
bug: converter dropped everything but translation).
"""

from __future__ import annotations

import numpy as np
import pytest

from etu.formats.git import (
    Commit,
    GitScene,
    Part,
    Snapshot,
    compose,
    decompose,
    identity,
)
from etu.formats.scene import Box, PointCloud


def _moved(scene: GitScene, part_id: str, t: int) -> list[float]:
    return scene.decode(t)[part_id]["position"]


def _translation(dx: float, dy: float, dz: float) -> list[float]:
    m = np.eye(4)
    m[:3, 3] = [dx, dy, dz]
    return m.flatten().tolist()


def _ball(id_: str) -> Part:
    return Part(id=id_, geometry=PointCloud(points=[0, 0, 0]))


# ── frame decoding ──────────────────────────────────────────────────────


def test_frame_0_no_commits():
    """No commits: frame 0 is exactly the base pose (origin, identity)."""
    scene = GitScene(title="t", fps=10, duration_frames=1, parts=[_ball("p")])
    assert _moved(scene, "p", 0) == [0.0, 0.0, 0.0]


def test_single_translation():
    """One commit moves the part by that delta."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=2,
        parts=[_ball("p")],
        commits=[Commit(0, {"p": _translation(10, 0, 0)})],
    )
    assert _moved(scene, "p", 0) == pytest.approx([10, 0, 0])


def test_cumulative_translations():
    """Two translation commits accumulate rather than each being absolute."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=3,
        parts=[_ball("p")],
        commits=[
            Commit(0, {"p": _translation(5, 0, 0)}),
            Commit(1, {"p": _translation(3, 0, 0)}),
        ],
    )
    assert _moved(scene, "p", 0) == pytest.approx([5, 0, 0])
    assert _moved(scene, "p", 1) == pytest.approx([8, 0, 0])


def test_keyframe_seek_uses_nearest_snapshot():
    """decode() should replay from the closest snapshot, not always frame 0."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=5,
        parts=[_ball("p")],
        commits=[Commit(i, {"p": _translation(5, 0, 0)}) for i in range(4)],
        keyframes=[
            Snapshot(
                1,
                {
                    "p": {
                        "position": [10, 0, 0],
                        "quaternion": [0, 0, 0, 1],
                        "scale": [1, 1, 1],
                        "opacity": 1.0,
                    }
                },
            )
        ],
    )
    # keyframe(1)=10, + commit(2) + commit(3) = 10 + 5 + 5 = 20
    assert _moved(scene, "p", 3) == pytest.approx([20, 0, 0])


def test_multi_part_independent_transforms():
    """Two parts move independently within the same commit."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=2,
        parts=[_ball("blue"), _ball("red")],
        commits=[
            Commit(0, {"blue": _translation(2, 0, 0), "red": _translation(0, 3, 0)})
        ],
    )
    assert _moved(scene, "blue", 0) == pytest.approx([2, 0, 0])
    assert _moved(scene, "red", 0) == pytest.approx([0, 3, 0])


def test_generate_keyframes_intervals_and_values():
    """generate_keyframes lays snapshots at the interval with correct accumulated state."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=10,
        parts=[_ball("p")],
        commits=[Commit(i, {"p": _translation(1, 0, 0)}) for i in range(9)],
    )
    snaps = scene.generate_keyframes(interval=3)
    assert [s.t for s in snaps] == [0, 3, 6, 9]
    assert snaps[1].poses["p"]["position"] == pytest.approx([4, 0, 0])
    assert snaps[3].poses["p"]["position"] == pytest.approx([9, 0, 0])


def test_backward_playback_matches_forward():
    """Rewinding from a later snapshot must agree with replaying forward.

    This is the new v0.3 capability the archived format never had — decode()
    picks whichever direction (replay from an earlier snapshot, or rewind
    from a later one) is closer, and both must land on the same pose.
    """
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=20,
        parts=[_ball("p")],
        commits=[Commit(i, {"p": _translation(1, 0, 0)}) for i in range(19)],
    )
    scene.generate_keyframes(
        interval=30
    )  # only the base snapshot, forces rewind from `final`
    scene.final = Snapshot(19, scene._replay_to(None, 19))
    forward = scene._replay_to(None, 10)
    backward = scene._rewind_to(scene.final, 10)
    assert forward["p"]["position"] == pytest.approx(
        backward["p"]["position"], abs=1e-9
    )


def test_rotation_and_scale_survive_a_commit():
    """A commit that only rotates/scales (no translation) must still apply."""
    quat_90z = [0.0, 0.0, 0.70710678, 0.70710678]  # 90deg around Z
    m = compose([0, 0, 0], quat_90z, [2.0, 2.0, 2.0])
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=2,
        parts=[_ball("p")],
        commits=[Commit(0, {"p": m.flatten().tolist()})],
    )
    pose = scene.decode(0)["p"]
    assert pose["scale"] == pytest.approx([2.0, 2.0, 2.0], abs=1e-6)
    assert pose["quaternion"] == pytest.approx(quat_90z, abs=1e-6)


# ── validation ──────────────────────────────────────────────────────────


def test_validate_non_pointcloud_part_accepted():
    """A part with no point geometry (e.g. a Box) is valid, given a final model."""
    scene = GitScene(
        title="t", fps=10, duration_frames=1, parts=[Part("cube", geometry=Box())]
    )
    scene.final = Snapshot(0, scene.decode(0))
    assert scene.validate() == []


def test_validate_bad_commit_matrix_size():
    """A commit matrix that is not 16 floats is caught."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=2,
        parts=[_ball("p")],
        commits=[Commit(0, {"p": [1, 0, 0]})],
    )
    problems = scene.validate()
    assert any("16" in p for p in problems), problems


def test_validate_unknown_part_in_commit():
    """A commit referencing a part id absent from the base is caught."""
    scene = GitScene(
        title="t",
        fps=10,
        duration_frames=2,
        parts=[_ball("p")],
        commits=[Commit(0, {"ghost": identity()})],
    )
    problems = scene.validate()
    assert any("unknown" in p.lower() for p in problems), problems


def test_validate_missing_final_model():
    """A scene with no final snapshot is flagged (final is mandatory in v0.3)."""
    scene = GitScene(title="t", fps=10, duration_frames=3, parts=[_ball("p")])
    problems = scene.validate()
    assert any("final" in p.lower() for p in problems), problems


# ── geometry round-trips ──────────────────────────────────────────────────


def test_box_geometry_roundtrip():
    part = Part(
        "cubie", geometry=Box(size=[0.94, 0.94, 0.94], face_colors={"px": "#B71234"})
    )
    scene = GitScene(title="t", fps=30, duration_frames=1, parts=[part])
    scene.final = Snapshot(0, scene.decode(0))
    again = GitScene.from_dict(scene.to_dict())
    assert again.parts[0].geometry.size == [0.94, 0.94, 0.94]
    assert again.parts[0].geometry.face_colors == {"px": "#B71234"}


def test_pointcloud_geometry_roundtrip():
    part = Part(
        "cloud",
        geometry=PointCloud(points=[0, 0, 0, 1, 1, 1], colors=[1, 0, 0, 0, 1, 0]),
    )
    scene = GitScene(title="t", fps=30, duration_frames=1, parts=[part])
    scene.final = Snapshot(0, scene.decode(0))
    again = GitScene.from_dict(scene.to_dict())
    assert again.parts[0].geometry.points == [0, 0, 0, 1, 1, 1]
    assert again.parts[0].geometry.colors == [1, 0, 0, 0, 1, 0]


# ── mixed scenes / legacy compat ────────────────────────────────────────


def test_mixed_geometry_parts_decode_together():
    """A pointcloud part and a box part in the same scene both decode fine."""
    scene = GitScene(
        title="mixed",
        fps=30,
        duration_frames=3,
        parts=[_ball("cloud"), Part("cube", geometry=Box())],
        commits=[
            Commit(0, {"cloud": _translation(1, 0, 0), "cube": _translation(1, 0, 0)})
        ],
    )
    frame = scene.decode(2)
    assert "cloud" in frame and "cube" in frame
    assert frame["cloud"]["position"] == pytest.approx([1, 0, 0])


def test_v02_file_still_loads():
    """A v0.2-shaped dict (shared base point array, point_indices) still reads."""
    v02 = {
        "format": "mmi-git",
        "version": "0.2",
        "meta": {
            "title": "old",
            "fps": 10,
            "duration_frames": 2,
            "source": "x",
            "events": [],
        },
        "base": {"points": [0, 0, 0, 5, 0, 0], "colors": None},
        "parts": [{"id": "ball", "label": "ball", "point_indices": [0, 1]}],
        "commits": [{"t": 0, "transforms": {"ball": identity()}}],
        "keyframes": [],
        "layers": [],
    }
    scene = GitScene.from_dict(v02)
    assert scene.parts[0].id == "ball"
    assert scene.parts[0].geometry.points == [0, 0, 0, 5, 0, 0]
    assert scene.final is not None  # backfilled since v0.2 files never had one


def test_unknown_geometry_kind_rejected_by_validator():
    """A bad geometry kind is a clear validator error, not a silent default.

    Construction fails fast (geometry_from_dict raises) rather than the
    archived design's lenient parse + validate()-time flag, so this is
    checked through the validator entry point that a real user hits.
    """
    from etu.formats.validate import validate_dict

    bad = {
        "format": "mmi-git",
        "version": "0.3",
        "meta": {
            "title": "t",
            "fps": 10,
            "duration_frames": 1,
            "source": "x",
            "events": [],
        },
        "base": {"parts": [{"id": "p", "geometry": {"kind": "sphere"}}]},
        "commits": [],
        "keyframes": [],
        "final": None,
        "layers": [],
    }
    report = validate_dict(bad)
    assert not report.ok
    assert any("sphere" in p.lower() for p in report.problems)


def test_decompose_inverts_compose():
    """compose then decompose returns the original pose, for a non-trivial pose."""
    pos, quat, scale = (
        [1.0, 2.0, 3.0],
        [0.0, 0.70710678, 0.0, 0.70710678],
        [1.0, 2.0, 0.5],
    )
    m = compose(pos, quat, scale)
    out = decompose(m)
    assert out["position"] == pytest.approx(pos, abs=1e-6)
    assert out["scale"] == pytest.approx(scale, abs=1e-6)
    assert abs(abs(sum(a * b for a, b in zip(out["quaternion"], quat))) - 1.0) < 1e-6
