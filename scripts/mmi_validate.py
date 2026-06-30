#!/usr/bin/env python3
"""Standalone reference validator for the **mmi-lite** scene format.

This is the contract checker between Person A (who emits `mmi-lite` JSON) and
Person B (whose `.mmi` compiler consumes it). It is deliberately **zero-import**
beyond the Python standard library and does NOT depend on the `mmi` package, so
Person B can vendor this single file to validate compiler input/golden files
without our codebase.

It validates structure, the geometry tagged-union, keyframe tracks (including the
optional `opacity` lifetime field), and the constant-vertex-count invariant that
morph `frames` must satisfy. Errors fail the file; warnings are advisory.

Usage:
    python scripts/mmi_validate.py scene.json [more.json ...]
    python scripts/mmi_validate.py data/samples/        # all *.json in a dir
    python scripts/mmi_validate.py --quiet scene.json   # only print failures

Exit code 0 if every file is valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FORMAT_NAME = "mmi-lite"
SUPPORTED_VERSIONS = {"0.1"}
GEOMETRY_KINDS = {"box", "pointcloud", "line", "surface"}
BOX_FACES = {"px", "nx", "py", "ny", "pz", "nz"}


class Report:
    """Collects errors (fail) and warnings (advisory) with JSON-pointer paths."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


# ---- small typed-field helpers -------------------------------------------------

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num_list(rep: Report, where: str, v, *, length: int | None = None,
              mult_of: int | None = None) -> bool:
    if not isinstance(v, list) or not all(_is_num(x) for x in v):
        rep.err(where, "must be a list of numbers")
        return False
    if length is not None and len(v) != length:
        rep.err(where, f"expected {length} numbers, got {len(v)}")
        return False
    if mult_of is not None and len(v) % mult_of != 0:
        rep.err(where, f"length {len(v)} is not a multiple of {mult_of}")
        return False
    return True


def _is_hex_color(v) -> bool:
    if not isinstance(v, str) or not v.startswith("#"):
        return False
    h = v[1:]
    return len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h)


# ---- geometry ------------------------------------------------------------------

def _check_morph_frames(rep: Report, where: str, frames, key: str,
                        expect_len: int | None = None) -> None:
    """`frames`: sparse keyframes that must share a constant vertex count."""
    if not isinstance(frames, list) or not frames:
        rep.err(where, "`frames` must be a non-empty list")
        return
    vcount = None
    for i, f in enumerate(frames):
        fw = f"{where}[{i}]"
        if not isinstance(f, dict):
            rep.err(fw, "frame must be an object")
            continue
        if not isinstance(f.get("t"), int) or isinstance(f.get("t"), bool):
            rep.err(fw, "frame `t` must be an integer")
        verts = f.get(key)
        if not _num_list(rep, f"{fw}.{key}", verts):
            continue
        if expect_len is not None and len(verts) != expect_len:
            rep.err(f"{fw}.{key}", f"expected {expect_len} values, got {len(verts)}")
        if vcount is None:
            vcount = len(verts)
        elif len(verts) != vcount:
            rep.err(fw, f"vertex count {len(verts)} != {vcount} (morph frames must be constant)")
        if f.get("colors") is not None and not _num_list(rep, f"{fw}.colors", f["colors"]):
            pass
    if not any(isinstance(f, dict) and f.get("t") == 0 for f in frames):
        rep.warn(where, "no frame at t=0; viewer holds the earliest frame before it")


def _check_geometry(rep: Report, where: str, geo) -> None:
    if not isinstance(geo, dict):
        rep.err(where, "geometry must be an object")
        return
    kind = geo.get("kind")
    if kind not in GEOMETRY_KINDS:
        rep.err(where, f"unknown geometry kind {kind!r} (expected one of {sorted(GEOMETRY_KINDS)})")
        return

    if kind == "box":
        _num_list(rep, f"{where}.size", geo.get("size"), length=3)
        fc = geo.get("face_colors")
        if not isinstance(fc, dict):
            rep.err(f"{where}.face_colors", "must be an object keyed by face")
        else:
            missing = BOX_FACES - set(fc)
            if missing:
                rep.warn(f"{where}.face_colors", f"missing faces {sorted(missing)} (will default-color)")
            for k, v in fc.items():
                if k not in BOX_FACES:
                    rep.warn(f"{where}.face_colors", f"unexpected face key {k!r}")
                if not _is_hex_color(v):
                    rep.err(f"{where}.face_colors.{k}", f"{v!r} is not a #hex color")

    elif kind == "pointcloud":
        if geo.get("frames") is not None:
            _check_morph_frames(rep, f"{where}.frames", geo["frames"], "positions")
        elif geo.get("points") is not None:
            _num_list(rep, f"{where}.points", geo["points"], mult_of=3)
        else:
            rep.err(where, "pointcloud needs `points` or `frames`")
        if geo.get("colors") is not None:
            _num_list(rep, f"{where}.colors", geo["colors"], mult_of=3)

    elif kind == "line":
        if geo.get("frames") is not None:
            _check_morph_frames(rep, f"{where}.frames", geo["frames"], "points")
        elif geo.get("points") is not None:
            _num_list(rep, f"{where}.points", geo["points"], mult_of=3)
        else:
            rep.err(where, "line needs `points` or `frames`")
        if geo.get("color") is not None and not _is_hex_color(geo["color"]):
            rep.err(f"{where}.color", f"{geo['color']!r} is not a #hex color")

    elif kind == "surface":
        rows, cols = geo.get("rows"), geo.get("cols")
        if not (isinstance(rows, int) and isinstance(cols, int) and rows > 1 and cols > 1):
            rep.err(where, "surface needs integer rows>1 and cols>1")
            return
        expect = rows * cols * 3
        if geo.get("frames") is not None:
            _check_morph_frames(rep, f"{where}.frames", geo["frames"], "positions", expect_len=expect)
        elif geo.get("positions") is not None:
            _num_list(rep, f"{where}.positions", geo["positions"], length=expect)
        else:
            rep.err(where, "surface needs `positions` or `frames`")
        if geo.get("opacity") is not None and not (_is_num(geo["opacity"]) and 0 <= geo["opacity"] <= 1):
            rep.err(f"{where}.opacity", "must be a number in [0,1]")


# ---- track / keyframes ---------------------------------------------------------

def _check_track(rep: Report, where: str, track, duration: int) -> None:
    if not isinstance(track, list) or not track:
        rep.err(where, "track must be a non-empty list of keyframes")
        return
    last_t = None
    for i, k in enumerate(track):
        kw = f"{where}[{i}]"
        if not isinstance(k, dict):
            rep.err(kw, "keyframe must be an object")
            continue
        t = k.get("t")
        if not isinstance(t, int) or isinstance(t, bool):
            rep.err(kw, "`t` must be an integer")
        else:
            if not (0 <= t < duration):
                rep.err(kw, f"t={t} out of range [0,{duration})")
            if last_t is not None and t < last_t:
                rep.warn(kw, f"t={t} is out of order (after {last_t}); viewer sorts but emit sorted")
            last_t = t
        _num_list(rep, f"{kw}.position", k.get("position"), length=3)
        if k.get("quaternion") is not None:
            _num_list(rep, f"{kw}.quaternion", k["quaternion"], length=4)
        if k.get("scale") is not None:
            _num_list(rep, f"{kw}.scale", k["scale"], length=3)
        op = k.get("opacity")
        if op is not None and not (_is_num(op) and 0 <= op <= 1):
            rep.err(f"{kw}.opacity", "must be a number in [0,1]")


# ---- top level -----------------------------------------------------------------

def validate(doc) -> Report:
    rep = Report()
    if not isinstance(doc, dict):
        rep.err("$", "top-level must be a JSON object")
        return rep

    if doc.get("format") != FORMAT_NAME:
        rep.err("$.format", f"expected {FORMAT_NAME!r}, got {doc.get('format')!r}")
    if doc.get("version") not in SUPPORTED_VERSIONS:
        rep.warn("$.version", f"version {doc.get('version')!r} not in {sorted(SUPPORTED_VERSIONS)}")

    meta = doc.get("meta")
    duration = 1
    if not isinstance(meta, dict):
        rep.err("$.meta", "must be an object")
    else:
        if not (isinstance(meta.get("fps"), int) and meta["fps"] > 0):
            rep.err("$.meta.fps", "must be a positive integer")
        df = meta.get("duration_frames")
        if not (isinstance(df, int) and df >= 1):
            rep.err("$.meta.duration_frames", "must be an integer >= 1")
        else:
            duration = df
        if meta.get("events") is not None and not isinstance(meta["events"], list):
            rep.err("$.meta.events", "must be a list")
        if "title" not in meta:
            rep.warn("$.meta.title", "missing title")

    layers = doc.get("layers", [])
    layer_ids = set()
    if not isinstance(layers, list):
        rep.err("$.layers", "must be a list")
    else:
        for i, l in enumerate(layers):
            if not isinstance(l, dict) or "id" not in l:
                rep.err(f"$.layers[{i}]", "layer needs an `id`")
                continue
            if l["id"] in layer_ids:
                rep.err(f"$.layers[{i}]", f"duplicate layer id {l['id']!r}")
            layer_ids.add(l["id"])
            if l.get("color") is not None and not _is_hex_color(l["color"]):
                rep.warn(f"$.layers[{i}].color", f"{l['color']!r} is not a #hex color")

    objects = doc.get("objects")
    if not isinstance(objects, list):
        rep.err("$.objects", "must be a list")
    else:
        seen_ids = set()
        for i, o in enumerate(objects):
            ow = f"$.objects[{i}]"
            if not isinstance(o, dict):
                rep.err(ow, "object must be an object")
                continue
            oid = o.get("id")
            if not isinstance(oid, str) or not oid:
                rep.err(ow, "object needs a non-empty string `id`")
            elif oid in seen_ids:
                rep.err(ow, f"duplicate object id {oid!r}")
            else:
                seen_ids.add(oid)
            layer = o.get("layer", "default")
            if layer != "default" and layer not in layer_ids:
                rep.err(f"{ow}.layer", f"references unknown layer {layer!r}")
            _check_geometry(rep, f"{ow}.geometry", o.get("geometry"))
            _check_track(rep, f"{ow}.track", o.get("track"), duration)

    anns = doc.get("annotations", [])
    if anns is not None and not isinstance(anns, list):
        rep.err("$.annotations", "must be a list")
    elif isinstance(anns, list):
        for i, a in enumerate(anns):
            aw = f"$.annotations[{i}]"
            if not isinstance(a, dict):
                rep.err(aw, "annotation must be an object")
                continue
            if not isinstance(a.get("t"), int):
                rep.err(f"{aw}.t", "must be an integer")
            _num_list(rep, f"{aw}.position", a.get("position"), length=3)
            if not isinstance(a.get("text"), str):
                rep.err(f"{aw}.text", "must be a string")

    return rep


def _iter_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out.extend(sorted(path.glob("*.json")))
        else:
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate mmi-lite scene JSON (zero-dependency reference checker).")
    ap.add_argument("paths", nargs="+", help="scene .json files or directories")
    ap.add_argument("--quiet", action="store_true", help="only print files that fail")
    ap.add_argument("--no-warnings", action="store_true", help="suppress warnings")
    args = ap.parse_args(argv)

    files = _iter_files(args.paths)
    if not files:
        print("no .json files found", file=sys.stderr)
        return 1

    all_ok = True
    for f in files:
        try:
            doc = json.loads(f.read_text())
        except FileNotFoundError:
            print(f"✗ {f}: file not found")
            all_ok = False
            continue
        except json.JSONDecodeError as e:
            print(f"✗ {f}: invalid JSON — {e}")
            all_ok = False
            continue

        rep = validate(doc)
        all_ok = all_ok and rep.ok
        if rep.ok and args.quiet:
            continue
        mark = "✓" if rep.ok else "✗"
        nobj = len(doc.get("objects", [])) if isinstance(doc, dict) else "?"
        print(f"{mark} {f}  ({nobj} objects)")
        for e in rep.errors:
            print(f"    ERROR  {e}")
        if not args.no_warnings:
            for w in rep.warnings:
                print(f"    warn   {w}")

    print(f"\n{'all valid' if all_ok else 'VALIDATION FAILED'} — {len(files)} file(s) checked")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
