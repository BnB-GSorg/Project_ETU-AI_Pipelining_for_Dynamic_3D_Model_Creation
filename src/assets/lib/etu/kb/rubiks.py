"""What a Rubik's cube is, and what its moves do.

The cube is 26 cubies on a 3x3x3 lattice with the centre cell empty. Each
cubie's colours are fixed in its *own* frame, decided once from the cell it
starts in — so when a cubie rotates, its colours ride along and end up facing
the right way with no bookkeeping.

A move turns one layer 90 degrees. Sign convention is the standard one: a
plain move is clockwise seen from outside that face, so `U` is -90 degrees
about +Y (right-hand rule makes +90 about +Y look anticlockwise from above).
"""

from __future__ import annotations

import re

import numpy as np

from etu.formats.git import Part, default_pose
from etu.formats.scene import Box
from etu.model import Model

# Standard Western colour scheme, keyed by the face normal each colour sits on.
COLORS = {
    "py": "#ffffff",  # up     white
    "ny": "#ffd500",  # down   yellow
    "px": "#b71234",  # right  red
    "nx": "#ff5800",  # left   orange
    "pz": "#009b48",  # front  green
    "nz": "#0046ad",  # back   blue
}
INNER = "#1a1a1a"  # faces buried inside the cube

AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

# move -> (axis, which layer, degrees)
FACES = {
    "U": ("y", 1, -90),
    "D": ("y", -1, 90),
    "R": ("x", 1, -90),
    "L": ("x", -1, 90),
    "F": ("z", 1, -90),
    "B": ("z", -1, 90),
}

MOVE_TOKEN = re.compile(r"^([UDRLFB])(['2]?)$")

CUBIE_SIZE = 0.94  # slightly under 1 so the gaps between cubies stay visible


def operations() -> list[str]:
    """Every legal move name: the six faces, each plain, primed and doubled."""
    return [f"{face}{suffix}" for face in FACES for suffix in ("", "'", "2")]


def parse_moves(text: str) -> list[str]:
    """Turn "R U R' U2" into ["R", "U", "R'", "U2"]. Raises on anything else."""
    moves = []
    for token in text.replace(",", " ").split():
        if not MOVE_TOKEN.match(token):
            raise ValueError(
                f"not a cube move: {token!r} (expected one of {', '.join(operations())})"
            )
        moves.append(token)
    return moves


def invert(moves: list[str]) -> list[str]:
    """The sequence that undoes `moves` — reversed, with each move reversed."""
    out = []
    for move in reversed(moves):
        if move.endswith("2"):
            out.append(move)  # a half turn undoes itself
        elif move.endswith("'"):
            out.append(move[0])
        else:
            out.append(move + "'")
    return out


def turn(move: str) -> tuple[str, int, float]:
    """Resolve a move name to (axis, layer, degrees)."""
    match = MOVE_TOKEN.match(move)
    if not match:
        raise ValueError(f"not a cube move: {move!r}")
    face, suffix = match.groups()
    axis, layer, degrees = FACES[face]
    if suffix == "'":
        degrees = -degrees
    elif suffix == "2":
        degrees *= 2
    return axis, layer, float(degrees)


def rotation(axis: str, degrees: float) -> np.ndarray:
    """A 4x4 rotation about a world axis through the cube's centre."""
    angle = np.radians(degrees)
    c, s = np.cos(angle), np.sin(angle)
    m = np.eye(4)
    if axis == "x":
        m[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == "y":
        m[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else:
        m[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return m


def layer_members(model: Model, move: str) -> list[str]:
    """The parts a move turns, judged by where they are *now*, not where they began."""
    axis, layer, _ = turn(move)
    index = AXIS_INDEX[axis]
    return [
        pid
        for pid, pose in model.poses.items()
        if round(pose["position"][index]) == layer
    ]


def face_colors(cell: tuple[int, int, int]) -> dict[str, str]:
    """Which of a cubie's six faces show colour, decided by its starting cell."""
    x, y, z = cell
    outward = {
        "px": x == 1,
        "nx": x == -1,
        "py": y == 1,
        "ny": y == -1,
        "pz": z == 1,
        "nz": z == -1,
    }
    return {face: (COLORS[face] if shows else INNER) for face, shows in outward.items()}


def _layer_name(cell: tuple[int, int, int]) -> str:
    return {3: "corners", 2: "edges", 1: "centres"}[sum(1 for v in cell if v)]


def solved() -> Model:
    """A solved cube: 26 cubies, each at its home cell, unrotated."""
    model = Model(concept="rubiks_cube")
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                if (x, y, z) == (0, 0, 0):
                    continue  # the core is never visible
                cell = (x, y, z)
                pid = f"cubie_{x + 1}{y + 1}{z + 1}"
                model.parts.append(
                    Part(
                        id=pid,
                        label=f"{_layer_name(cell)[:-1]} {cell}",
                        geometry=Box(
                            size=[CUBIE_SIZE] * 3, face_colors=face_colors(cell)
                        ),
                        layer=_layer_name(cell),
                    )
                )
                pose = default_pose()
                pose["position"] = [float(x), float(y), float(z)]
                model.poses[pid] = pose
    return model


def build_cube(scramble: str | list[str] | None = None) -> Model:
    """A cube in the state reached by applying `scramble` to a solved cube."""
    from etu.ops.executor import apply_move  # here to avoid an import cycle

    model = solved()
    for move in _as_moves(scramble):
        apply_move(model, move)
    return model


def is_solved(model: Model) -> bool:
    """True when every cubie is home and unrotated."""
    for part in model.parts:
        pose = model.poses[part.id]
        home = [float(int(c) - 1) for c in part.id.rsplit("_", 1)[1]]
        if [round(v) for v in pose["position"]] != [int(v) for v in home]:
            return False
        if abs(abs(pose["quaternion"][3]) - 1.0) > 1e-6:
            return False
    return True


def layers() -> list[dict[str, str]]:
    """Viewer layer definitions, so corners/edges/centres can be toggled."""
    return [
        {"id": "corners", "name": "Corners (8)", "color": COLORS["px"]},
        {"id": "edges", "name": "Edges (12)", "color": COLORS["pz"]},
        {"id": "centres", "name": "Centres (6)", "color": COLORS["ny"]},
    ]


def _as_moves(scramble: str | list[str] | None) -> list[str]:
    if not scramble:
        return []
    return parse_moves(scramble) if isinstance(scramble, str) else list(scramble)
