"""Compiler round-trip: mmi-lite <-> mmi-git, both directions.

Covers the archived bugs directly:
  bug 1 — the old converter only went lite->git; git->lite produced garbage.
  bug 3 — it dropped rotation/scale/opacity, so an animated scene (rotation
          only, no translation) compiled to zero commits.
"""

from __future__ import annotations

import math

import pytest

from etu.formats.compiler import round_trip_error, to_git, to_lite
from etu.formats.scene import Keyframe, PointCloud, Scene, SceneObject


def _rotating_square_wave_scene(n_frames: int = 20) -> Scene:
    """A scene that only rotates — no translation — like fourier_stack's harmonics."""
    track = []
    for i in range(n_frames):
        angle = math.pi * i / (n_frames - 1)
        q = [0.0, 0.0, math.sin(angle / 2), math.cos(angle / 2)]
        track.append(Keyframe(t=i, position=[0, 0, 0], quaternion=q))
    obj = SceneObject(
        id="harmonic_1", geometry=PointCloud(points=[1, 0, 0] * 10), track=track
    )
    return Scene(title="rotating", fps=30, duration_frames=n_frames, objects=[obj])


def test_rotation_only_scene_compiles_to_nonzero_commits():
    """Archived bug 3: a rotation-only animation must not compile to 0 commits."""
    scene = _rotating_square_wave_scene()
    git = to_git(scene)
    assert git.commit_count > 0


def test_round_trip_error_within_tolerance():
    scene = _rotating_square_wave_scene()
    assert round_trip_error(scene) < 1e-6


def test_git_to_lite_direction_exists_and_is_not_garbage():
    """Archived bug 1: git->lite must reconstruct real objects, not zero of them."""
    scene = _rotating_square_wave_scene()
    git = to_git(scene)
    back = to_lite(git)
    assert len(back.objects) == 1
    assert len(back.objects[0].track) > 0


def test_scale_and_opacity_survive_lite_git_lite():
    obj = SceneObject(
        id="fader",
        geometry=PointCloud(points=[0, 0, 0]),
        track=[
            Keyframe(t=0, position=[0, 0, 0], scale=[1, 1, 1], opacity=0.0),
            Keyframe(t=10, position=[0, 0, 0], scale=[3, 3, 3], opacity=1.0),
        ],
    )
    scene = Scene(title="t", duration_frames=11, objects=[obj])
    git = to_git(scene)
    back = to_lite(git)

    from etu.formats.scene import sample_track

    original_mid = sample_track(obj.track, 5)
    round_tripped_mid = sample_track(back.objects[0].track, 5)
    assert round_tripped_mid["scale"] == pytest.approx(original_mid["scale"], abs=1e-6)
    assert round_tripped_mid["opacity"] == pytest.approx(
        original_mid["opacity"], abs=1e-6
    )


def test_static_scene_compiles_to_zero_commits():
    """A scene where nothing moves should have no commits — the flip side of bug 3.

    The lone keyframe sits at the identity pose, matching the compiler's
    starting assumption, so there is nothing to commit.
    """
    obj = SceneObject(
        id="still",
        geometry=PointCloud(points=[0, 0, 0]),
        track=[Keyframe(0, [0, 0, 0])],
    )
    scene = Scene(title="t", duration_frames=5, objects=[obj])
    git = to_git(scene)
    assert git.commit_count == 0


def test_compiled_scene_validates():
    scene = _rotating_square_wave_scene()
    git = to_git(scene)
    assert git.validate() == []


def test_compiled_scene_final_matches_last_frame():
    scene = _rotating_square_wave_scene(n_frames=8)
    git = to_git(scene)
    from etu.formats.scene import sample_track

    expected = sample_track(scene.objects[0].track, scene.duration_frames - 1)
    assert git.final.poses["harmonic_1"]["quaternion"] == pytest.approx(
        expected["quaternion"], abs=1e-6
    )
