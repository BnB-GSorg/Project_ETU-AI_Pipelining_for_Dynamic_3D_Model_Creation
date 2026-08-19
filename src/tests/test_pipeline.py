"""The operation pipeline: instruction -> plan -> commits -> compiled file."""

from __future__ import annotations

import json

import pytest

from etu.brain import plan as planner
from etu.formats import compiler
from etu.formats.validate import validate_dict, validate_file
from etu.kb import rubiks
from etu.kb.database import known, lookup, search
from etu.ops import sequence

SCRAMBLE = "R U R' U'"


# ── knowledge base ──────────────────────────────────────────────────────


def test_lookup_by_name_and_alias():
    assert lookup("rubiks_cube").name == "rubiks_cube"
    assert lookup("cube").name == "rubiks_cube"
    assert lookup("Rubik's Cube").name == "rubiks_cube"
    assert lookup("banana") is None


def test_search_finds_concept_in_a_sentence():
    assert search("here is a video of a rubiks cube spinning").name == "rubiks_cube"
    assert search("a video of a kettle") is None


def test_known_lists_concepts():
    assert "rubiks_cube" in known()


# ── planning ────────────────────────────────────────────────────────────


def test_literal_move_sequence_is_parsed_without_a_model():
    plan = planner.instruct("U L' U' L", lookup("rubiks_cube"))
    assert plan.route == "parsed"
    assert plan.operations == ["U", "L'", "U'", "L"]


def test_solve_intent_inverts_the_history():
    history = rubiks.parse_moves(SCRAMBLE)
    plan = planner.instruct(
        "please solve the cube", lookup("rubiks_cube"), history=history
    )
    assert plan.route == "intent"
    assert plan.operations == rubiks.invert(history)


def test_solve_without_history_abstains():
    plan = planner.instruct("solve it", lookup("rubiks_cube"), history=[])
    assert not plan.ok
    assert "unknown" in plan.rationale or "already" in plan.rationale


def test_undo_intent_reverses_only_the_last_move():
    history = rubiks.parse_moves("R U F")
    plan = planner.instruct("undo that", lookup("rubiks_cube"), history=history)
    assert plan.operations == ["F'"]


def test_unknown_instruction_abstains_when_offline():
    plan = planner.instruct("make me a sandwich", lookup("rubiks_cube"))
    assert not plan.ok
    assert plan.route == "none"


def test_model_route_accepts_catalogue_moves():
    def fake_chat(system, user):
        return json.dumps({"operations": ["R", "U'"], "rationale": "because"})

    plan = planner.instruct("do the thing", lookup("rubiks_cube"), chat_fn=fake_chat)
    assert plan.route == "model"
    assert plan.operations == ["R", "U'"]


def test_model_route_rejects_moves_outside_the_catalogue():
    """A model that invents moves must be refused, not trusted."""

    def fake_chat(system, user):
        return '```json\n{"operations": ["R", "TWIST"], "rationale": "made up"}\n```'

    plan = planner.instruct("do the thing", lookup("rubiks_cube"), chat_fn=fake_chat)
    assert not plan.ok
    assert "TWIST" in plan.rationale


def test_model_route_survives_a_chatty_reply():
    def fake_chat(system, user):
        return 'Sure! Here you go:\n```json\n{"operations": ["D"], "rationale": "ok"}\n```\nHope that helps.'

    plan = planner.instruct("do the thing", lookup("rubiks_cube"), chat_fn=fake_chat)
    assert plan.operations == ["D"]


def test_model_route_handles_unparseable_reply():
    plan = planner.instruct(
        "do it", lookup("rubiks_cube"), chat_fn=lambda s, u: "no json here"
    )
    assert not plan.ok
    assert plan.route == "model"


# ── execution ───────────────────────────────────────────────────────────


def test_run_records_a_commit_per_frame_and_an_event_per_move():
    model = rubiks.build_cube(SCRAMBLE)
    moves = rubiks.invert(rubiks.parse_moves(SCRAMBLE))
    run = sequence.run(model, moves, frames_per_move=6)

    assert len(run.commits) == len(moves) * 6
    assert len(run.events) == len(moves)
    assert all(c.op for c in run.commits)  # every commit knows its move


def test_one_commit_per_move_when_asked():
    model = rubiks.build_cube(SCRAMBLE)
    moves = rubiks.invert(rubiks.parse_moves(SCRAMBLE))
    run = sequence.run(model, moves, frames_per_move=1, hold_frames=0)
    assert len(run.commits) == len(moves)


def test_run_does_not_mutate_the_original_model():
    model = rubiks.build_cube(SCRAMBLE)
    before = [list(model.poses[p.id]["position"]) for p in model.parts]
    sequence.run(model, ["U", "R"])
    after = [list(model.poses[p.id]["position"]) for p in model.parts]
    assert before == after


# ── compilation ─────────────────────────────────────────────────────────


def _compiled():
    info = lookup("rubiks_cube")
    model = info.build(SCRAMBLE)
    run = sequence.run(model, info.solve(rubiks.parse_moves(SCRAMBLE)))
    return compiler.from_execution(model, run, layers=info.layers), run


def test_compiled_scene_is_valid():
    git, _ = _compiled()
    assert git.validate() == []


def test_compiled_scene_replays_to_the_solved_state():
    """Replaying every commit lands on the state the executor finished in.

    Compared with a tolerance because the two sides get there differently:
    the executor snaps to the lattice after each move, while decoding
    multiplies the commit matrices straight through.
    """
    git, run = _compiled()
    decoded = git.decode(git.duration_frames - 1)
    for pid, pose in run.final.poses.items():
        assert decoded[pid]["position"] == pytest.approx(pose["position"], abs=1e-9)


def test_compiled_scene_plays_backward_to_the_scramble():
    """Rewinding to frame 0 must give back the scrambled cube we started from."""
    git, run = _compiled()
    start = git.decode(0)
    for pid, pose in run.initial.poses.items():
        assert start[pid]["position"] == pose["position"]


def test_compiled_scene_keeps_the_parts_and_their_colours():
    git, _ = _compiled()
    assert len(git.parts) == 26
    assert git.parts[0].geometry.face_colors is not None


def test_compiled_scene_validates_through_the_file_validator(tmp_path):
    git, _ = _compiled()
    path = git.save(tmp_path / "cube.mmi")
    report = validate_file(path)
    assert report.ok, report.problems
    assert report.fmt == "mmi-git"


def test_media_block_round_trips():
    git, _ = _compiled()
    git.media = {"video": "clip.mp4", "poster": None}
    again = validate_dict(json.loads(json.dumps(git.to_dict())))
    assert again.ok, again.problems


def test_media_block_references_a_missing_file_rather_than_failing():
    block = compiler.media_block("not-a-real-file.mp4")
    assert block["video"] == "not-a-real-file.mp4"


def test_commit_op_label_survives_saving(tmp_path):
    git, _ = _compiled()
    path = git.save(tmp_path / "cube.mmi")
    reloaded = json.loads(path.read_text())
    assert reloaded["commits"][0]["op"]
