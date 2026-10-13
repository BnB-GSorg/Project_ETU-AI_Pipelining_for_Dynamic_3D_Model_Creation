"""The CLI entry point: it must import, and expose every documented command.

`src/main.py` is not imported by the pipeline tests, which is exactly how a
syntax error there (a second bare string before `from __future__`) shipped
undetected. Importing it here turns that whole class of breakage into a test
failure: a bad `from __future__`, a broken import, or a command that drops out
of the registry.
"""

from __future__ import annotations

import main

EXPECTED_COMMANDS = {
    "search",
    "model",
    "instruct",
    "execute",
    "compile",
    "validate",
    "serve",
    "demo",
    "self-test",
    "watch",
}


def test_main_entrypoint_imports():
    """The command hub compiles and imports without a SyntaxError."""
    assert main.VERSION


def test_main_exposes_every_documented_command():
    """No command documented in the README falls out of the registry."""
    missing = EXPECTED_COMMANDS - set(main.COMMANDS)
    assert not missing, f"commands missing from main.COMMANDS: {sorted(missing)}"
