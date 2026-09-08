"""Shared paths, the file registry, and the engine's terminal I/O.

by MCHIGM — 20260812
"""

import sys
from pathlib import Path

# Resolved from this file, so the engine works from any working directory.
SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

# The engine's library lives under assets/lib. Put it on the import path so
# `import etu` works no matter where the interpreter is started from.
LIB = SRC / "assets" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

# The modules that make up the engine, with a one-line description each.
FILES = {
    "main.py": "Entry point — the command hub.",
    "lib.py": "Shared paths, file registry, terminal I/O (this file).",
    "assets/lib/etu/model.py": "A model: its parts and where each one sits.",
    "assets/lib/etu/formats/scene.py": "mmi-lite — objects with keyframe tracks.",
    "assets/lib/etu/formats/git.py": "mmi-git v0.3 — base, commits, final, media.",
    "assets/lib/etu/formats/compiler.py": "Compile a run of operations into mmi-git.",
    "assets/lib/etu/formats/validate.py": "Validate either format.",
    "assets/lib/etu/kb/database.py": "Concepts: properties, target state, operations.",
    "assets/lib/etu/kb/rubiks.py": "The cube: geometry, colours, and what moves do.",
    "assets/lib/etu/ops/executor.py": "Apply one operation, record it as a commit.",
    "assets/lib/etu/ops/sequence.py": "Run a sequence, collect the commit chain.",
    "assets/lib/etu/brain/llm.py": "Chat with a reasoning model — seven providers.",
    "assets/lib/etu/brain/plan.py": "Instruction text to an operation plan.",
    "assets/lib/etu/vision/cv.py": "Look at video frames, identify the object.",
    "assets/demo/viewer/index.html": "The player: orbit, scrub, play both ways.",
    "assets/demo/viewer/main.js": "Viewer logic — loads mmi-lite and mmi-git.",
}


def find(name):
    """Return the path to a project file, or None if it is not present."""
    path = SRC / name
    return path if path.exists() else None


class BASIC_IO:
    """Terminal input and output for the engine's command loop."""

    PROMPT = "etu> "

    def read(self):
        """Read one command. Returns None on Ctrl-D or Ctrl-C."""
        try:
            return input(self.PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def say(self, message):
        print(message)

    def warn(self, message):
        print(f"! {message}")

    def help(self, commands=None):
        """List commands, taking the descriptions from their docstrings."""
        self.say("\n  Pipeline commands:")
        for name, func in (commands or {}).items():
            first_line = (func.__doc__ or "").strip().splitlines()[0]
            self.say(f"    {name:<10} {first_line}")
        self.say("\n  Engine commands:")
        self.say(f"    {'help':<10} Show this message.")
        self.say(
            f"    {'files':<10} List the engine's files and whether each is present."
        )
        self.say(f"    {'version':<10} Show the engine version.")
        self.say(f"    {'exit':<10} Leave the engine.\n")

    def files(self):
        """List the registered files, marking any that are missing."""
        for name, description in FILES.items():
            mark = "+" if find(name) else "-"
            self.say(f"  {mark} {name:<26} {description}")

    def exit(self):
        """Say goodbye. Returns 1 so callers can treat it as 'stop'."""
        self.say("bye")
        return 1
