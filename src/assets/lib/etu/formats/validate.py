"""Validate a scene file of either format.

The format is read from the file's own `format` field rather than assumed from
the extension, because the old validator insisted on mmi-lite and rejected
perfectly good `.mmi` files with "expected 'mmi-lite', got 'mmi-git'" — an
error about its own assumption, not about the file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from etu.formats import git as git_format
from etu.formats import scene as lite_format
from etu.formats.git import GitScene
from etu.formats.scene import Scene

KNOWN = {lite_format.FORMAT: "mmi-lite", git_format.FORMAT: "mmi-git"}


@dataclass
class Report:
    """The outcome of validating one file."""

    path: Path
    fmt: str
    version: str
    ok: bool
    problems: list[str]
    summary: str = ""

    def __str__(self) -> str:
        head = f"{'OK  ' if self.ok else 'FAIL'} {self.path.name}  [{self.fmt} v{self.version}]"
        if self.summary:
            head += f"  {self.summary}"
        return "\n".join([head] + [f"       - {p}" for p in self.problems])


def validate_file(path: str | Path) -> Report:
    path = Path(path)
    if not path.exists():
        return Report(path, "?", "?", False, [f"file not found: {path}"])

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return Report(path, "?", "?", False, [f"not valid JSON: {exc}"])

    if not isinstance(data, dict):
        return Report(path, "?", "?", False, ["top level of the file is not an object"])

    return validate_dict(data, path)


def validate_dict(data: dict[str, Any], path: Path | None = None) -> Report:
    path = path or Path("<memory>")
    fmt = str(data.get("format", ""))
    version = str(data.get("version", "?"))

    if fmt not in KNOWN:
        listed = ", ".join(sorted(KNOWN))
        got = repr(fmt) if fmt else "no 'format' field"
        return Report(
            path,
            fmt or "?",
            version,
            False,
            [f"unrecognised format: {got} (expected one of: {listed})"],
        )

    try:
        if fmt == lite_format.FORMAT:
            obj = Scene.from_dict(data)
            problems = obj.validate()
            summary = f"{len(obj.objects)} objects, {obj.duration_frames} frames"
        else:
            obj = GitScene.from_dict(data)
            problems = obj.validate()
            summary = f"{len(obj.parts)} parts, {obj.commit_count} commits, {obj.duration_frames} frames"
    except (KeyError, ValueError, TypeError) as exc:
        return Report(path, fmt, version, False, [f"cannot read as {fmt}: {exc}"])

    return Report(path, fmt, version, not problems, problems, summary)


def detect_format(path: str | Path) -> str | None:
    """Return 'mmi-lite', 'mmi-git', or None if the file does not say."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    fmt = data.get("format") if isinstance(data, dict) else None
    return fmt if fmt in KNOWN else None
