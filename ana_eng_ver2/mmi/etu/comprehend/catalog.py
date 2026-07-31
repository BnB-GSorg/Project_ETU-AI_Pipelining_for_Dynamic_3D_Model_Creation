"""Closed-set catalog: machine-readable description of every template.

This is what makes E3 *closed-set and low-risk*: the comprehension model is only
ever allowed to pick one of these concepts and fill these params (validated +
clamped here). It cannot invent geometry. Keep this in sync with the templates.
"""

from __future__ import annotations

from mmi.etu.templates import available

# Per concept: a "when to use" hint, and a param schema the classifier must obey.
# Numeric params carry a [min, max] range; enums carry allowed values.
CATALOG: dict[str, dict] = {
    "complex_surface": {
        "when": "The video explains a COMPLEX function f(z), Riemann surfaces, "
                "domain coloring, poles/zeros, or |f(z)| over the complex plane.",
        "params": {
            "func": {"type": "enum", "values": ["z^2", "z^3-1", "1/z", "(z^2-1)/(z^2+1)"], "default": "z^3-1"},
            "extent": {"type": "float", "range": [0.5, 5.0], "default": 1.6},
            "n": {"type": "int", "range": [12, 80], "default": 44},
            "height": {"type": "float", "range": [0.2, 4.0], "default": 1.4},
            "clip": {"type": "float", "range": [0.5, 10.0], "default": 3.0},
            "frames": {"type": "int", "range": [20, 240], "default": 90},
        },
    },
    "graph_surface": {
        "when": "The video plots a real two-variable function z = f(x, y), a 3D "
                "graph/surface, a saddle, a Gaussian bump, ripples, or a heatmap of f(x,y).",
        "params": {
            "func": {"type": "enum", "values": ["saddle", "gaussian", "ripple", "monkey"], "default": "ripple"},
            "extent": {"type": "float", "range": [0.5, 6.0], "default": 3.0},
            "n": {"type": "int", "range": [12, 80], "default": 36},
            "height": {"type": "float", "range": [0.2, 4.0], "default": 1.6},
            "frames": {"type": "int", "range": [20, 240], "default": 80},
        },
    },
    "fourier_stack": {
        "when": "The video is about FOURIER series/analysis: building a square "
                "wave (or other signal) from sine/cosine harmonics, decomposition, convergence.",
        "params": {
            "harmonics": {"type": "int", "range": [1, 20], "default": 9},
            "samples": {"type": "int", "range": [50, 600], "default": 220},
            "spacing": {"type": "float", "range": [0.2, 2.0], "default": 0.9},
            "yscale": {"type": "float", "range": [0.2, 4.0], "default": 1.3},
            "frames": {"type": "int", "range": [20, 240], "default": 90},
        },
    },
    "taylor_series": {
        "when": "The video is about TAYLOR/Maclaurin series or polynomial "
                "approximation of a function (sin, cos, exp, 1/(1-x), log(1+x)) by "
                "successively higher-degree terms.",
        "params": {
            "func": {"type": "enum", "values": ["sin", "cos", "exp", "geometric", "log1p"], "default": "sin"},
            "terms": {"type": "int", "range": [1, 12], "default": 6},
            "spacing": {"type": "float", "range": [0.2, 2.0], "default": 0.9},
            "yscale": {"type": "float", "range": [0.2, 4.0], "default": 1.3},
            "frames": {"type": "int", "range": [20, 240], "default": 90},
        },
    },
    "vector_field": {
        "when": "The video shows a VECTOR FIELD: arrows indicating direction/"
                "magnitude over space, rotation/curl, sources/sinks, saddles, or flow.",
        "params": {
            "field": {"type": "enum", "values": ["rotation", "source", "saddle", "shear", "spiral"], "default": "rotation"},
            "density": {"type": "int", "range": [3, 8], "default": 5},
            "scale": {"type": "float", "range": [0.1, 1.5], "default": 0.45},
            "extent": {"type": "float", "range": [0.5, 4.0], "default": 2.0},
        },
    },
    "linear_transform": {
        "when": "The video is about LINEAR ALGEBRA transformations: a matrix acting "
                "on space/vectors, shear, rotation, scaling, reflection, projection, "
                "determinant, eigenvectors, basis vectors.",
        "params": {
            "matrix": {"type": "enum", "values": ["shear", "scale", "rotation", "reflection", "projection", "shear3d"], "default": "shear"},
            "n": {"type": "int", "range": [3, 8], "default": 5},
            "frames": {"type": "int", "range": [20, 240], "default": 70},
        },
    },
    "parametric_surface": {
        "when": "The video shows a PARAMETRIC SURFACE or 3D geometric shape defined "
                "by parameters: torus, sphere, helicoid, Mobius strip, surfaces of revolution.",
        "params": {
            "shape": {"type": "enum", "values": ["torus", "sphere", "helicoid", "mobius"], "default": "torus"},
            "n": {"type": "int", "range": [16, 80], "default": 48},
            "frames": {"type": "int", "range": [20, 240], "default": 90},
        },
    },
}


def _consistency_check() -> None:
    missing = set(available()) - set(CATALOG)
    extra = set(CATALOG) - set(available())
    if missing or extra:
        raise RuntimeError(f"catalog out of sync with templates: missing={missing} extra={extra}")


_consistency_check()


def prompt_catalog() -> dict:
    """Compact catalog for embedding in the LLM prompt."""
    return {
        c: {"when": d["when"],
            "params": {k: {kk: vv for kk, vv in v.items()} for k, v in d["params"].items()}}
        for c, d in CATALOG.items()
    }


def validate_params(concept: str, params: dict) -> dict:
    """Coerce/clamp model-proposed params to the schema; drop unknown keys."""
    schema = CATALOG[concept]["params"]
    out: dict = {}
    for key, spec in schema.items():
        if key not in params:
            continue
        val = params[key]
        if spec["type"] == "enum":
            if val in spec["values"]:
                out[key] = val
        elif spec["type"] == "int":
            try:
                lo, hi = spec["range"]
                out[key] = int(max(lo, min(hi, int(round(float(val))))))
            except (TypeError, ValueError):
                pass
        elif spec["type"] == "float":
            try:
                lo, hi = spec["range"]
                out[key] = float(max(lo, min(hi, float(val))))
            except (TypeError, ValueError):
                pass
    return out
