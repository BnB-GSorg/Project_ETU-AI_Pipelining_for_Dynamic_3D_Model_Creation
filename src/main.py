"""Project ETU — command hub.

Run a command directly:      python main.py demo
or start the loop:           python main.py

The pipeline each command is a step of:

    video ─► vision ─► state ─► model ─► operations ─► commits ─► .mmi ─► viewer
                                  ▲          ▲
                          knowledge base   instruction

Author: DuBoLEE, MCHIGM
"""

from __future__ import annotations

import logging
import shlex
import sys
from pathlib import Path

import lib
from etu.brain import plan as planner
from etu.formats import compiler
from etu.formats.validate import validate_file
from etu.kb import database, rubiks
from etu.ops import sequence
from etu.vision import cv

VERSION = "0.3.0"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("etu")

OUT_DIR = lib.ROOT / ".env" / "demo"
VIEWER_URL = "http://localhost:{port}/src/viewer/"


# ── commands ────────────────────────────────────────────────────────────


def cmd_search(io, args):
    """search <text> — what does the knowledge base know about this?"""
    if not args:
        io.warn("usage: search <text>   e.g. search rubik's cube")
        return
    info = database.search(" ".join(args)) or database.lookup(" ".join(args))
    if info is None:
        io.warn(
            f"nothing known about that. known concepts: {', '.join(database.known())}"
        )
        return
    io.say(info.describe())


def cmd_model(io, args):
    """model <concept> [--scramble "R U R'"] — build a model and describe it."""
    flags, rest = _flags(args)
    name = " ".join(rest) or "rubiks_cube"
    info = database.lookup(name) or database.search(name)
    if info is None or info.build is None:
        io.warn(f"cannot build {name!r}. known concepts: {', '.join(database.known())}")
        return

    scramble = flags.get("scramble", "")
    try:
        model = info.build(scramble)
    except ValueError as exc:
        io.warn(str(exc))
        return

    io.say(f"{info.name}: {len(model.parts)} parts")
    io.say(f"  scramble : {scramble or '(none — solved)'}")
    io.say(f"  solved   : {rubiks.is_solved(model)}")
    io.say(f"  layers   : {', '.join(v['id'] for v in info.layers)}")


def cmd_instruct(io, args):
    """instruct "<text>" [--concept X] [--history "R U"] — text to operations."""
    flags, rest = _flags(args)
    text = " ".join(rest)
    if not text:
        io.warn('usage: instruct "solve it" --history "R U R\' U\'"')
        return

    info = (
        database.lookup(flags.get("concept", ""))
        or database.search(text)
        or database.lookup("rubiks_cube")
    )
    history = rubiks.parse_moves(flags["history"]) if flags.get("history") else []
    result = planner.instruct(text, info, history=history, chat_fn=_brain(flags))
    io.say(str(result))
    if result.rationale:
        io.say(f"  because: {result.rationale}")


def cmd_execute(io, args):
    """execute [--concept X] [--scramble S] [--ops "U R"] [--instruct "solve it"]"""
    run, _info, _model = _build_and_run(io, _flags(args)[0])
    if run is None:
        return
    io.say(f"{len(run.commits)} commits over {run.duration_frames} frames")
    io.say(f"  solved at the end: {rubiks.is_solved(run.model)}")
    for event in run.events[:12]:
        io.say(f"  t={event['t']:<4} {event['label']}")
    if len(run.events) > 12:
        io.say(f"  ... and {len(run.events) - 12} more")


def cmd_compile(io, args):
    """compile [--scramble S] [--ops ...] [--video f.mp4] [--out file.mmi]"""
    flags, _ = _flags(args)
    run, info, model = _build_and_run(io, flags)
    if run is None:
        return

    out = Path(flags.get("out") or OUT_DIR / f"{info.name}.mmi")
    git = compiler.from_execution(
        model,
        run,
        title=flags.get("title", f"{info.name} — {len(run.events)} moves"),
        fps=int(flags.get("fps", 30)),
        layers=info.layers,
        video=flags.get("video"),
    )
    problems = git.validate()
    git.save(out)

    io.say(f"wrote {out}")
    io.say(
        f"  parts {len(git.parts)} · commits {git.commit_count} · frames {git.duration_frames}"
    )
    io.say(f"  validate: {'OK' if not problems else problems}")
    io.say(f"  view: run 'serve', then open {_viewer_link(out)}")


def cmd_validate(io, args):
    """validate <file> — check an mmi-lite or mmi-git file."""
    if not args:
        io.warn("usage: validate <file.json|file.mmi>")
        return
    for name in args:
        io.say(str(validate_file(name)))


def cmd_serve(io, args):
    """serve [--port 8000] — serve the project so the viewer can load files."""
    import http.server
    import socketserver

    port = int((_flags(args)[0]).get("port", 8000))

    # The project root, not src/, because compiled files land in .env/demo/ and
    # a server rooted at src/ cannot reach outside itself.
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(lib.ROOT), **kw)

        def log_message(self, *a):
            pass  # the default handler logs every asset request; too noisy here

    io.say(f"serving {lib.ROOT} at {VIEWER_URL.format(port=port)}")
    io.say("ctrl-c to stop")
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        io.say("\nstopped")
    except OSError as exc:
        io.warn(f"cannot serve on port {port}: {exc}")


def cmd_demo(io, args):
    """demo — the whole pipeline, offline: scramble a cube, solve it, compile it."""
    flags, _ = _flags(args)
    scramble = flags.get("scramble", "R U R' U' F R F'")

    io.say("── ETU demo ─────────────────────────────────────────")
    info = database.lookup("rubiks_cube")
    io.say(f"1. concept   : {info.name} — {info.summary}")

    moves = rubiks.parse_moves(scramble)
    model = info.build(moves)
    io.say(f"2. model     : {len(model.parts)} cubies, scrambled with {scramble}")

    result = planner.instruct("solve the cube", info, history=moves)
    io.say(
        f"3. instruct  : 'solve the cube' -> {result.route} -> {' '.join(result.operations)}"
    )

    run = sequence.run(model, result.operations)
    io.say(f"4. execute   : {len(run.commits)} commits, {run.duration_frames} frames")
    io.say(f"               solved at the end: {rubiks.is_solved(run.model)}")

    out = OUT_DIR / "rubiks_solve.mmi"
    git = compiler.from_execution(
        model, run, title="Rubik's cube solving itself", fps=30, layers=info.layers
    )
    git.save(out)
    io.say(f"5. compile   : {out}")

    report = validate_file(out)
    io.say(
        f"6. validate  : {'OK' if report.ok else report.problems}  ({report.summary})"
    )
    io.say("")
    io.say(f"   run 'serve', then open:  {_viewer_link(out)}")


def cmd_self_test(io, args):
    """self-test — check the pipeline works without any network or API key."""
    checks, failures = [], []

    def check(name, condition, detail=""):
        checks.append((name, bool(condition), detail))
        if not condition:
            failures.append(name)

    info = database.lookup("rubiks cube")
    check("kb lookup by alias", info is not None and info.name == "rubiks_cube")
    check(
        "operation catalogue", len(info.operations) == 18, f"{len(info.operations)} ops"
    )

    moves = rubiks.parse_moves("R U R' U2")
    check("parse moves", moves == ["R", "U", "R'", "U2"])
    check("invert", rubiks.invert(["R", "U2"]) == ["U2", "R'"])

    model = info.build("R U R' U'")
    check("build scrambled", len(model.parts) == 26 and not rubiks.is_solved(model))

    solution = planner.instruct(
        "solve it", info, history=rubiks.parse_moves("R U R' U'")
    )
    check("instruct -> intent", solution.route == "intent" and solution.ok)

    run = sequence.run(model, solution.operations)
    check("execute solves it", rubiks.is_solved(run.model))
    check("commits recorded", len(run.commits) > 0, f"{len(run.commits)} commits")

    git = compiler.from_execution(model, run, layers=info.layers)
    check("compiles clean", git.validate() == [])
    check("decode round-trip", git.decode(git.duration_frames - 1) == git.final.poses)

    literal = planner.instruct("U L' U' L", info)
    check(
        "instruct -> parsed", literal.route == "parsed" and len(literal.operations) == 4
    )

    refused = planner.instruct("make me a sandwich", info)
    check("abstains when unknown", not refused.ok)

    if cv.available():
        check("opencv present", True, "vision available")
    else:
        checks.append(("opencv", True, "SKIP — not installed, vision disabled"))

    for name, ok, detail in checks:
        io.say(
            f"  {'PASS' if ok else 'FAIL'}  {name}{f'  ({detail})' if detail else ''}"
        )
    io.say(f"self-test: {'PASS' if not failures else 'FAIL ' + ', '.join(failures)}")


def cmd_watch(io, args):
    """watch <video.mp4> — look at a video and say what object is in it."""
    if not args:
        io.warn("usage: watch <video.mp4>")
        return
    video = Path(args[0])
    if not video.exists():
        io.warn(f"no such file: {video}")
        return
    if not cv.available():
        io.warn("opencv is not installed; cannot look at frames")
        return

    frames = cv.extract_frames(video, OUT_DIR / "frames")
    io.say(f"extracted {len(frames)} frames")
    io.say(str(cv.read_state(frames)))


# ── plumbing ────────────────────────────────────────────────────────────


def _build_and_run(io, flags):
    """Shared by execute and compile: build a model, decide moves, run them."""
    name = flags.get("concept", "rubiks_cube")
    info = database.lookup(name) or database.search(name)
    if info is None or info.build is None:
        io.warn(f"cannot build {name!r}. known: {', '.join(database.known())}")
        return None, None, None

    try:
        scramble = rubiks.parse_moves(flags.get("scramble", ""))
        model = info.build(scramble)

        if flags.get("ops"):
            moves = rubiks.parse_moves(flags["ops"])
        else:
            result = planner.instruct(
                flags.get("instruct", "solve it"),
                info,
                history=scramble,
                chat_fn=_brain(flags),
            )
            if not result.ok:
                io.warn(f"no operations to run: {result.rationale}")
                return None, None, None
            moves = result.operations
    except ValueError as exc:
        io.warn(str(exc))
        return None, None, None

    return sequence.run(model, moves), info, model


def _brain(flags):
    """A chat function for the planner, or None to stay fully offline."""
    if "provider" not in flags:
        return None
    from etu.brain.llm import LLMConfig, chat_json

    cfg = LLMConfig(provider=flags["provider"], model=flags.get("model", ""))
    return lambda system, user: chat_json(system, user, cfg)


def _flags(args):
    """Split ["--a", "1", "rest"] into ({"a": "1"}, ["rest"]). Bare flags are "true"."""
    flags, rest, i = {}, [], 0
    while i < len(args):
        token = args[i]
        if token.startswith("--"):
            key = token[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = "true"
                i += 1
        else:
            rest.append(token)
            i += 1
    return flags, rest


def _viewer_link(path, port=8000):
    """The URL that opens the viewer on a compiled file.

    The viewer page lives at /src/viewer/, so a file elsewhere in the project
    is reached by climbing back out of those two directories.
    """
    relative = Path(path).resolve().relative_to(lib.ROOT.resolve()).as_posix()
    return f"{VIEWER_URL.format(port=port)}?file=../../{relative}"


COMMANDS = {
    "search": cmd_search,
    "model": cmd_model,
    "instruct": cmd_instruct,
    "execute": cmd_execute,
    "compile": cmd_compile,
    "validate": cmd_validate,
    "serve": cmd_serve,
    "demo": cmd_demo,
    "self-test": cmd_self_test,
    "watch": cmd_watch,
}


# ── command loop ────────────────────────────────────────────────────────


def dispatch(io, command):
    """Run one command. Returns False when the engine should stop."""
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        io.warn(f"could not read that command: {exc}")
        return True

    if not parts:
        return True

    name, args = parts[0], parts[1:]

    if name in ("exit", "quit"):
        io.exit()
        return False
    if name == "help":
        io.help(COMMANDS)
    elif name == "files":
        io.files()
    elif name == "version":
        io.say(f"Project ETU {VERSION}")
    elif name in COMMANDS:
        COMMANDS[name](io, args)
    else:
        io.warn(f"unknown command: {name} (try 'help')")
    return True


def loop(io):
    """Read and run commands until the user stops or input ends."""
    while True:
        command = io.read()
        if command is None:
            io.exit()
            return
        if not dispatch(io, command):
            return


def main(argv=None):
    """Run one command from argv, or start the interactive loop."""
    argv = sys.argv[1:] if argv is None else argv
    io = lib.BASIC_IO()

    if argv:
        dispatch(io, shlex.join(argv))
        return 0

    io.say(f"Project ETU {VERSION} — type 'help' for commands.")
    loop(io)
    return 0


if __name__ == "__main__":
    sys.exit(main())
