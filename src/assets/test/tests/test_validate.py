"""Validator: format auto-detection, accept/reject matrix.

Archived bug 2: the old validator assumed mmi-lite and rejected valid
mmi-git files with "expected 'mmi-lite', got 'mmi-git'" — an error about its
own assumption, not the file. Here the format is read from the file itself.
"""

from __future__ import annotations

from etu.formats.compiler import to_git
from etu.formats.scene import Keyframe, PointCloud, Scene, SceneObject
from etu.formats.validate import detect_format, validate_dict


def _lite_scene_dict() -> dict:
    obj = SceneObject(
        id="a", geometry=PointCloud(points=[0, 0, 0]), track=[Keyframe(0, [0, 0, 0])]
    )
    return Scene(title="t", duration_frames=1, objects=[obj]).to_dict()


def _git_scene_dict() -> dict:
    scene = Scene.from_dict(_lite_scene_dict())
    return to_git(scene).to_dict()


def test_valid_mmi_lite_accepted():
    report = validate_dict(_lite_scene_dict())
    assert report.ok, report.problems
    assert report.fmt == "mmi-lite"


def test_valid_mmi_git_accepted():
    """The exact case the archived validator got wrong: a good .mmi file."""
    report = validate_dict(_git_scene_dict())
    assert report.ok, report.problems
    assert report.fmt == "mmi-git"


def test_unrecognised_format_field_reports_true_reason():
    report = validate_dict({"format": "something-else", "version": "1"})
    assert not report.ok
    assert "something-else" in report.problems[0]
    assert "mmi-lite" in report.problems[0] and "mmi-git" in report.problems[0]


def test_missing_format_field_reports_clearly():
    report = validate_dict({"meta": {"title": "t"}})
    assert not report.ok
    assert "no 'format' field" in report.problems[0]


def test_corrupt_lite_scene_rejected_with_real_reason():
    d = _lite_scene_dict()
    d["objects"][0]["track"] = []  # empty track is invalid
    report = validate_dict(d)
    assert not report.ok
    assert any("empty track" in p for p in report.problems)


def test_corrupt_git_scene_rejected_with_real_reason():
    d = _git_scene_dict()
    d["commits"].append({"t": 0, "transforms": {"a": [1, 0, 0]}})  # bad matrix size
    report = validate_dict(d)
    assert not report.ok
    assert any("16" in p for p in report.problems)


def test_incomplete_dict_missing_fields_rejected():
    report = validate_dict({"format": "mmi-lite", "version": "0.2"})
    assert not report.ok  # meta/objects absent -> defaults to an empty, invalid scene


def test_detect_format_lite_and_git():
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        lite_path = Path(d) / "a.json"
        git_path = Path(d) / "a.mmi"
        lite_path.write_text(json.dumps(_lite_scene_dict()))
        git_path.write_text(json.dumps(_git_scene_dict()))
        assert detect_format(lite_path) == "mmi-lite"
        assert detect_format(git_path) == "mmi-git"


def test_detect_format_unknown_file_returns_none():
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "bad.json"
        path.write_text(json.dumps({"hello": "world"}))
        assert detect_format(path) is None
