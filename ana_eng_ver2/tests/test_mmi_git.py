"""Tests for mmi-git format — frame computation, keyframes, validation."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.formats.mmi_git import (
    MmiGitScene, PartSpec, Commit, KeyFrame, GitGeometry,
    identity_matrix, translation_matrix,
)


def test_frame_0_no_commits():
    """Frame 0 with no commits should return base positions unchanged."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=1,
        base_points=[0, 0, 0, 5, 0, 0],
        parts=[PartSpec("ball", "ball", [0, 1])],
    )
    result = scene.compute_frame(0)
    pts = np.array(result["ball"]).reshape(-1, 3)
    assert pts.shape == (2, 3)
    assert np.allclose(pts[0], [0, 0, 0]), f"got {pts[0]}"
    assert np.allclose(pts[1], [5, 0, 0]), f"got {pts[1]}"


def test_single_translation():
    """Apply one translation commit to all points."""
    T = translation_matrix(10, 0, 0)
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=2,
        base_points=[0, 0, 0, 5, 0, 0],
        parts=[PartSpec("ball", "ball", [0, 1])],
        commits=[Commit(0, {"ball": T})],
    )
    result = scene.compute_frame(0)
    pts = np.array(result["ball"]).reshape(-1, 3)
    assert np.allclose(pts[0], [10, 0, 0]), f"got {pts[0]}"
    assert np.allclose(pts[1], [15, 0, 0]), f"got {pts[1]}"


def test_cumulative_translations():
    """Two translation commits should accumulate."""
    T1 = translation_matrix(5, 0, 0)
    T2 = translation_matrix(3, 0, 0)
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=3,
        base_points=[0, 0, 0],
        parts=[PartSpec("p", "p", [0])],
        commits=[
            Commit(0, {"p": T1}),
            Commit(1, {"p": T2}),
        ],
    )
    # Frame 0: one commit applied → x=5
    f0 = np.array(scene.compute_frame(0)["p"]).flatten()
    assert np.allclose(f0, [5, 0, 0]), f"got {f0}"
    # Frame 1: two commits applied → x=8
    f1 = np.array(scene.compute_frame(1)["p"]).flatten()
    assert np.allclose(f1, [8, 0, 0]), f"got {f1}"


def test_keyframe_seek():
    """compute_frame should use the nearest keyframe, not always the base."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=5,
        base_points=[0, 0, 0],
        parts=[PartSpec("p", "p", [0])],
        commits=[
            Commit(0, {"p": translation_matrix(5, 0, 0)}),   # base→+5
            Commit(1, {"p": translation_matrix(5, 0, 0)}),   # +5→+10
            Commit(2, {"p": translation_matrix(5, 0, 0)}),   # +10→+15
            Commit(3, {"p": translation_matrix(5, 0, 0)}),   # +15→+20
        ],
        # Keyframe at frame 1 stores position x=10
        keyframes=[KeyFrame(1, {"p": [10, 0, 0]})],
    )
    # Frame 2: keyframe(1) + commit(2) = 10 + 5 = 15
    f2 = np.array(scene.compute_frame(2)["p"]).flatten()
    assert np.allclose(f2, [15, 0, 0]), f"got {f2}"

    # Frame 3: keyframe(1) + commit(2) + commit(3) = 10 + 5 + 5 = 20
    f3 = np.array(scene.compute_frame(3)["p"]).flatten()
    assert np.allclose(f3, [20, 0, 0]), f"got {f3}"


def test_multi_part():
    """Two parts with independent transforms."""
    T_move_blue = translation_matrix(2, 0, 0)
    T_move_red = translation_matrix(0, 3, 0)
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=2,
        base_points=[0, 0, 0, 5, 0, 0],  # index 0 = blue, 1 = red
        parts=[
            PartSpec("blue", "blue ball", [0]),
            PartSpec("red", "red ball", [1]),
        ],
        commits=[Commit(0, {"blue": T_move_blue, "red": T_move_red})],
    )
    f0 = scene.compute_frame(0)
    blue = np.array(f0["blue"]).flatten()
    red = np.array(f0["red"]).flatten()
    assert np.allclose(blue, [2, 0, 0]), f"blue got {blue}"
    assert np.allclose(red, [5, 3, 0]), f"red got {red}"


def test_generate_keyframes():
    """generate_keyframes should pre-compute snapshots."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=10,
        base_points=[0, 0, 0],
        parts=[PartSpec("p", "p", [0])],
        commits=[
            Commit(i, {"p": translation_matrix(1, 0, 0)}) for i in range(9)
        ],
    )
    kfs = scene.generate_keyframes(interval=3)
    assert len(kfs) == 4  # frames 0, 3, 6, 9
    assert kfs[0].t == 0
    assert kfs[1].t == 3
    assert kfs[2].t == 6
    assert kfs[3].t == 9
    # Keyframe at t=3: commits t=0,1,2,3 applied → 4 translates → x=4
    pts = np.array(kfs[1].parts["p"]).flatten()
    assert np.allclose(pts, [4, 0, 0]), f"got {pts}"
    # Keyframe at t=9: all 9 commits (t=0..8) applied → x=9
    pts9 = np.array(kfs[3].parts["p"]).flatten()
    assert np.allclose(pts9, [9, 0, 0]), f"got {pts9}"


def test_validate_empty_base_accepted():
    """Empty base_points is valid (for scenes with only non-pointcloud parts)."""
    geom = GitGeometry(kind="box", size=[1, 1, 1])
    part = PartSpec("cube", "A box", geometry=geom)
    scene = MmiGitScene(title="t", fps=10, duration_frames=1,
                        base_points=[], parts=[part])
    probs = scene.validate()
    assert not probs, f"Expected clean, got {probs}"


def test_validate_bad_commit():
    """Commit with wrong matrix size should be caught."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=2,
        base_points=[0, 0, 0],
        parts=[PartSpec("p", "p", [0])],
        commits=[Commit(0, {"p": [1, 0, 0]})],  # only 3 values, not 16
    )
    probs = scene.validate()
    assert any("16" in p for p in probs), f"got {probs}"


def test_validate_unknown_part():
    """Commit referencing a part not in the parts list should be caught."""
    scene = MmiGitScene(
        title="t", fps=10, duration_frames=2,
        base_points=[0, 0, 0],
        parts=[PartSpec("p", "p", [0])],
        commits=[Commit(0, {"unknown_part": identity_matrix()})],
    )
    probs = scene.validate()
    assert any("unknown" in p.lower() for p in probs), f"got {probs}"


# ── New geometry-type tests ──

def test_box_geometry_roundtrip():
    """Box geometry should survive serialization round-trip."""
    geom = GitGeometry(kind="box", size=[0.94, 0.94, 0.94],
                       face_colors={"px": "#B71234", "nx": "#FF5800"})
    part = PartSpec("cubie", "Corner", geometry=geom)
    scene = MmiGitScene(title="t", fps=30, duration_frames=10,
                        base_points=[0, 0, 0],
                        parts=[part], commits=[])
    d = scene.to_dict()
    scene2 = MmiGitScene.from_dict(d)
    p = scene2.parts[0]
    assert p.geom_kind == "box"
    assert p.geometry.size == [0.94, 0.94, 0.94]
    assert p.geometry.face_colors == {"px": "#B71234", "nx": "#FF5800"}


def test_surface_geometry_roundtrip():
    """Surface geometry should survive serialization round-trip."""
    positions = [i * 0.1 for i in range(12)]  # 4 vertices flat
    geom = GitGeometry(kind="surface", rows=2, cols=2,
                       positions=positions, surface_color="#ff0000",
                       opacity=0.5, wireframe=True)
    part = PartSpec("surf", "Surface", geometry=geom)
    scene = MmiGitScene(title="t", fps=30, duration_frames=10,
                        base_points=[],
                        parts=[part], commits=[])
    d = scene.to_dict()
    scene2 = MmiGitScene.from_dict(d)
    p = scene2.parts[0]
    assert p.geom_kind == "surface"
    assert p.geometry.rows == 2
    assert p.geometry.cols == 2
    assert p.geometry.opacity == 0.5
    assert p.geometry.wireframe is True


def test_line_geometry_roundtrip():
    """Line geometry should survive serialization round-trip."""
    geom = GitGeometry(kind="line", positions=[0, 0, 0, 1, 1, 1],
                       surface_color="#00ff00", line_width=3.0)
    part = PartSpec("curve", "Line", geometry=geom)
    scene = MmiGitScene(title="t", fps=30, duration_frames=10,
                        base_points=[],
                        parts=[part], commits=[])
    d = scene.to_dict()
    scene2 = MmiGitScene.from_dict(d)
    p = scene2.parts[0]
    assert p.geom_kind == "line"
    assert p.geometry.surface_color == "#00ff00"
    assert p.geometry.line_width == 3.0


def test_legacy_no_geometry_field():
    """Part without geometry field should default to pointcloud."""
    part = PartSpec("p1", "Old part", [0, 1, 2])
    assert part.geom_kind == "pointcloud"
    assert part.geometry is None
    # Serialization should not emit geometry field for legacy parts
    d = part.to_dict()
    assert "geometry" not in d
    assert d["point_indices"] == [0, 1, 2]


def test_mixed_parts():
    """Scene with mixed geometry types should validate and compute."""
    T = translation_matrix(1, 0, 0)
    geom_box = GitGeometry(kind="box", size=[1, 1, 1],
                           face_colors={"px": "#ff0000"})
    scene = MmiGitScene(
        title="mixed", fps=30, duration_frames=3,
        base_points=[0, 0, 0, 2, 0, 0],
        parts=[
            PartSpec("cloud", "pointcloud part", point_indices=[0, 1]),
            PartSpec("cube", "box part", geometry=geom_box),
        ],
        commits=[
            Commit(0, {"cloud": T, "cube": T}),
            Commit(1, {"cloud": T, "cube": T}),
        ],
    )
    probs = scene.validate()
    assert not probs, f"Expected clean validation, got {probs}"
    # Both parts appear in compute_frame output
    f = scene.compute_frame(2)
    assert "cloud" in f
    assert "cube" in f  # box part has empty (0,3) array
    cloud_pts = np.array(f["cloud"]).reshape(-1, 3)
    assert np.allclose(cloud_pts[0], [2, 0, 0]), f"got {cloud_pts[0]}"
    # Box part has empty geometry since it's non-pointcloud
    cube_pts = np.array(f["cube"])
    assert cube_pts.size == 0, f"box part should have empty array, got {cube_pts}"


def test_validate_bad_geometry_kind():
    """Unknown geometry kind should be caught by validation."""
    geom = GitGeometry(kind="sphere")  # not a valid kind
    part = PartSpec("p", "bad", geometry=geom)
    scene = MmiGitScene(title="t", fps=30, duration_frames=10,
                        base_points=[], parts=[part], commits=[])
    probs = scene.validate()
    assert any("unknown geometry kind" in p.lower() or "sphere" in p.lower() for p in probs), f"got {probs}"


if __name__ == "__main__":
    # Manual test runner — iterate through all test functions and report results
    tests = [
        test_frame_0_no_commits,
        test_single_translation,
        test_cumulative_translations,
        test_keyframe_seek,
        test_multi_part,
        test_generate_keyframes,
        test_validate_empty_base_accepted,
        test_validate_bad_commit,
        test_validate_unknown_part,
        # New geometry-type tests
        test_box_geometry_roundtrip,
        test_surface_geometry_roundtrip,
        test_line_geometry_roundtrip,
        test_legacy_no_geometry_field,
        test_mixed_parts,
        test_validate_bad_geometry_kind,
    ]
    for test in tests:
        test()
        print(f"  PASS: {test.__name__}")
    print(f"\n{len(tests)} tests passed")
