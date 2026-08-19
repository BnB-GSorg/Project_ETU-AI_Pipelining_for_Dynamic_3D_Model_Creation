"""The cube: move parsing, the turn table, and that the maths actually closes."""

from __future__ import annotations

import pytest

from etu.kb import rubiks
from etu.ops import sequence
from etu.ops.executor import apply_move, snap


def test_solved_cube_has_26_cubies():
    model = rubiks.solved()
    assert len(model.parts) == 26
    assert len(model.poses) == 26
    assert rubiks.is_solved(model)


def test_centre_cell_is_absent():
    """The core is never visible, so it is not a part."""
    model = rubiks.solved()
    assert "cubie_111" not in model.part_ids()  # (0,0,0) -> index 1,1,1


def test_catalogue_is_eighteen_moves():
    ops = rubiks.operations()
    assert len(ops) == 18
    assert {"U", "U'", "U2", "B", "B'", "B2"} <= set(ops)


def test_parse_moves():
    assert rubiks.parse_moves("R U R' U2") == ["R", "U", "R'", "U2"]
    assert rubiks.parse_moves("") == []


def test_parse_rejects_nonsense():
    with pytest.raises(ValueError, match="not a cube move"):
        rubiks.parse_moves("R U banana")


def test_invert():
    assert rubiks.invert(["R"]) == ["R'"]
    assert rubiks.invert(["R'"]) == ["R"]
    assert rubiks.invert(["R2"]) == ["R2"]  # a half turn undoes itself
    assert rubiks.invert(["R", "U"]) == ["U'", "R'"]


def test_four_quarter_turns_return_to_start():
    """The classic closure check: X X X X is the identity."""
    model = rubiks.solved()
    for _ in range(4):
        apply_move(model, "R")
        snap(model)
    assert rubiks.is_solved(model)


def test_move_then_inverse_returns_to_start():
    model = rubiks.solved()
    apply_move(model, "U")
    snap(model)
    assert not rubiks.is_solved(model)
    apply_move(model, "U'")
    snap(model)
    assert rubiks.is_solved(model)


def test_half_turn_equals_two_quarter_turns():
    a, b = rubiks.solved(), rubiks.solved()
    apply_move(a, "F2")
    snap(a)
    apply_move(b, "F")
    snap(b)
    apply_move(b, "F")
    snap(b)
    for pid in a.poses:
        assert a.poses[pid]["position"] == pytest.approx(
            b.poses[pid]["position"], abs=1e-6
        )


def test_a_move_turns_nine_cubies():
    """A face layer is 9 cells, one of which is the hidden core -> 8 parts."""
    model = rubiks.solved()
    assert len(rubiks.layer_members(model, "U")) == 9
    assert len(rubiks.layer_members(model, "R")) == 9


def test_scramble_then_solve_is_solved():
    scramble = "R U R' U' F R F'"
    model = rubiks.build_cube(scramble)
    assert not rubiks.is_solved(model)

    solution = rubiks.invert(rubiks.parse_moves(scramble))
    run = sequence.run(model, solution)
    assert rubiks.is_solved(run.model)


def test_face_colors_only_on_outer_faces():
    corner = rubiks.face_colors((1, 1, 1))
    assert corner["px"] == rubiks.COLORS["px"]
    assert corner["nx"] == rubiks.INNER

    centre = rubiks.face_colors((0, 1, 0))
    assert centre["py"] == rubiks.COLORS["py"]
    assert centre["px"] == rubiks.INNER


def test_layers_cover_every_part():
    model = rubiks.solved()
    declared = {v["id"] for v in rubiks.layers()}
    assert {p.layer for p in model.parts} <= declared
