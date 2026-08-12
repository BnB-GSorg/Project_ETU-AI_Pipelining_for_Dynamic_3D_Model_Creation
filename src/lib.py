"""

lib.py

by MCHIGM - 20260812

To provide a set of utility classes and functions, as well as acting as a hub
for file finding and calling.

"""

#############
# Imports
#############


# Built-in packages

from pathlib import Path

#############
# Paths
#############


# Resolved from this file, so the engine works from any working directory.
SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

# The scripts that make up the engine, with a one-line description each.
FILES = {
    "main.py": "Entry point - starts the engine and the command loop.",
    "lib.py": "Utility helpers and the file registry (this file).",
}


def find(name):
    """Return the path to a project file, or None if it is not present."""
    path = SRC / name
    return path if path.exists() else None


#############
# Basic CLI operations
#############


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

    def help(self):
        self.say("""
    Available commands:
      help      Show this message.
      files     List the engine's files and whether each one is present.
      version   Show the engine version.
      exit      Leave the engine.
""")

    def files(self):
        """List the registered files, marking any that are missing."""
        for name, description in FILES.items():
            mark = "+" if find(name) else "-"
            self.say(f"  {mark} {name:<10} {description}")

    def exit(self):
        """Say goodbye. Returns 1 so callers can treat it as 'stop'."""
        self.say("bye")
        return 1
