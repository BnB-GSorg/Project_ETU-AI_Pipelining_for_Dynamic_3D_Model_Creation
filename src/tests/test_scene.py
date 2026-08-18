"""mmi-lite: keyframe tracks, geometry validation, pose interpolation."""

from __future__ import annotations

import pytest

from etu.formats.scene import (
    Box,
    Keyframe,
    Layer,
    Line,
    PointCloud,
    Scene,
    SceneObject,
    Surface,
    sample_track,
)


def test_round_trip_to_dict_from_dict():
    scene = Scene(
        title="t",
        fps=24,
        duration_frames=10,
        objects=[
            SceneObject(
                id="a",
                geometry=PointCloud(points=[0, 0, 0]),
                track=[Keyframe(0, [1, 2, 3])],
            )
        ],
        layers=[Layer("l", "Layer", "#ffffff")],
    )
    again = Scene.from_dict(scene.to_dict())
    assert again.title == "t"
    assert again.objects[0].track[0].position == [1, 2, 3]
    assert again.layers[0].id == "l"


def test_validate_catches_empty_track():
    scene = Scene(
        title="t",
        duration_frames=5,
        objects=[SceneObject(id="a", geometry=PointCloud(), track=[])],
    )
    problems = scene.validate()
    assert any("empty track" in p for p in problems)


def test_validate_catches_duplicate_ids():
    obj = lambda: SceneObject(
        id="a", geometry=PointCloud(points=[0, 0, 0]), track=[Keyframe(0, [0, 0, 0])]
    )
    scene = Scene(title="t", duration_frames=1, objects=[obj(), obj()])
    problems = scene.validate()
    assert any("duplicate" in p for p in problems)


def test_validate_catches_out_of_range_keyframe():
    scene = Scene(
        title="t",
        duration_frames=3,
        objects=[
            SceneObject(
                id="a",
                geometry=PointCloud(points=[0, 0, 0]),
                track=[Keyframe(5, [0, 0, 0])],
            )
        ],
    )
    problems = scene.validate()
    assert any("outside" in p for p in problems)


def test_validate_catches_undeclared_layer():
    scene = Scene(
        title="t",
        duration_frames=1,
        layers=[Layer("known", "Known")],
        objects=[
            SceneObject(
                id="a",
                geometry=PointCloud(points=[0, 0, 0]),
                track=[Keyframe(0, [0, 0, 0])],
                layer="missing",
            )
        ],
    )
    problems = scene.validate()
    assert any("not declared" in p for p in problems)


def test_validate_pointcloud_length_mismatch():
    scene = Scene(
        title="t",
        duration_frames=1,
        objects=[
            SceneObject(
                id="a",
                geometry=PointCloud(points=[0, 0]),
                track=[Keyframe(0, [0, 0, 0])],
            )
        ],
    )
    problems = scene.validate()
    assert any("multiple of 3" in p for p in problems)


def test_validate_surface_vertex_count():
    scene = Scene(
        title="t",
        duration_frames=1,
        objects=[
            SceneObject(
                id="a",
                geometry=Surface(rows=2, cols=2, vertices=[0.0] * 5),
                track=[Keyframe(0, [0, 0, 0])],
            )
        ],
    )
    problems = scene.validate()
    assert any("expected 12" in p for p in problems)


def test_valid_scene_has_no_problems():
    scene = Scene(
        title="t",
        duration_frames=2,
        layers=[Layer("l", "L")],
        objects=[
            SceneObject(
                id="a", geometry=Box(), track=[Keyframe(0, [0, 0, 0])], layer="l"
            )
        ],
    )
    assert scene.validate() == []


# ── geometry kinds ──────────────────────────────────────────────────────


def test_all_four_geometry_kinds_round_trip():
    box, cloud, line, surf = (
        Box(size=[1, 2, 3]),
        PointCloud(points=[0, 0, 0]),
        Line(points=[0, 0, 0, 1, 1, 1]),
        Surface(rows=1, cols=2, vertices=[0.0] * 6),
    )
    for geom in (box, cloud, line, surf):
        obj = SceneObject(id="x", geometry=geom, track=[Keyframe(0, [0, 0, 0])])
        again = SceneObject.from_dict(obj.to_dict())
        assert type(again.geometry) is type(geom)


# ── pose sampling / interpolation ──────────────────────────────────────


def test_sample_track_before_first_and_after_last_clamps():
    track = [Keyframe(5, [1, 0, 0]), Keyframe(10, [2, 0, 0])]
    assert sample_track(track, 0)["position"] == [1, 0, 0]
    assert sample_track(track, 20)["position"] == [2, 0, 0]


def test_sample_track_lerps_position():
    track = [Keyframe(0, [0, 0, 0]), Keyframe(10, [10, 0, 0])]
    pose = sample_track(track, 5)
    assert pose["position"] == pytest.approx([5, 0, 0])


def test_sample_track_lerps_opacity():
    track = [Keyframe(0, [0, 0, 0], opacity=0.0), Keyframe(10, [0, 0, 0], opacity=1.0)]
    assert sample_track(track, 5)["opacity"] == pytest.approx(0.5)


def test_sample_track_slerps_quaternion():
    # 0deg to 180deg around Z; halfway should be 90deg around Z.
    q0, q1 = [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 1.0, 0.0]
    track = [
        Keyframe(0, [0, 0, 0], quaternion=q0),
        Keyframe(10, [0, 0, 0], quaternion=q1),
    ]
    mid = sample_track(track, 5)["quaternion"]
    assert mid == pytest.approx([0.0, 0.0, 0.70710678, 0.70710678], abs=1e-6)


def test_sample_track_empty_returns_identity():
    pose = sample_track([], 0)
    assert pose["position"] == [0.0, 0.0, 0.0]
    assert pose["quaternion"] == [0.0, 0.0, 0.0, 1.0]
