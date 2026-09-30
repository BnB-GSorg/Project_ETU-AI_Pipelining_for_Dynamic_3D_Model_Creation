"""Byte-for-byte reproducibility of the reference demo.

`src/main.py demo` is fully deterministic — no randomness, no timestamps —
so rebuilding it from the same operations on the pinned environment
(environment.yml / environment.lock.yml) must reproduce the exact same bytes
as the committed golden file.

Two guards live here:
  1. The golden file's sha256 is recorded, so an accidental edit is caught
     even though the rebuild itself is deterministic.
  2. The demo is rebuilt from scratch and compared byte-for-byte against
     the golden file, so a regression in the engine — or a drift in the
     numerical environment (numpy/OpenBLAS) — fails the suite.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from etu.brain import plan as planner
from etu.formats import compiler
from etu.kb import rubiks
from etu.kb.database import lookup
from etu.ops import sequence

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"
GOLDEN_FILE = GOLDEN_DIR / "rubiks_solve.mmi"

GOLDEN_SHA256 = "bb4330156f5b1941c592e0dd3f57b643830428ac20048ff0fabeb4c764dd3ccc"

# Exactly what cmd_demo in src/main.py runs, so the rebuild matches the
# golden file the demo command produces.
SCRAMBLE = "R U R' U' F R F'"
INSTRUCTION = "solve the cube"
TITLE = "Rubik's cube solving itself"


def _rebuild_demo(tmp_path: Path) -> Path:
    info = lookup("rubiks_cube")
    moves = rubiks.parse_moves(SCRAMBLE)
    model = info.build(moves)
    result = planner.instruct(INSTRUCTION, info, history=moves)
    assert result.ok, result.rationale
    run = sequence.run(model, result.operations)
    git = compiler.from_execution(model, run, title=TITLE, fps=30, layers=info.layers)
    assert git.validate() == []
    return git.save(tmp_path / "fresh.mmi")


def test_golden_file_is_committed_and_unchanged():
    assert GOLDEN_FILE.is_file(), "golden file missing — run `python src/main.py demo`"
    assert hashlib.sha256(GOLDEN_FILE.read_bytes()).hexdigest() == GOLDEN_SHA256


def test_demo_rebuilds_byte_identically(tmp_path):
    golden = GOLDEN_FILE.read_bytes()
    fresh = _rebuild_demo(tmp_path).read_bytes()
    assert fresh == golden, (
        "the demo no longer reproduces the golden file byte-for-byte.\n"
        "Either the engine changed its output (regression), or the pinned\n"
        "numerical environment (numpy/OpenBLAS) has drifted — see environment.yml."
    )
