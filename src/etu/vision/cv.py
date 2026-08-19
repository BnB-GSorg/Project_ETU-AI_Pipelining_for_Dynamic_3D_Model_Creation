"""Look at frames from a video and say what object is in them.

Deterministic OpenCV only — no vision model, no API key. What this can do
honestly is find the object and read the colours it is made of, which is
enough to recognise *which* concept we are looking at.

Reading a full cube state (all 54 facelets, including the three hidden faces)
from arbitrary footage is a much harder problem and is not attempted: when the
state cannot be read the caller is told so, and asks the user for the scramble
instead. Saying "I could not read this" is more useful than guessing wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Hue centres (OpenCV's 0..179 scale) for the six cube colours. Red wraps, so
# it gets two windows.
CUBE_HUES = {
    "white": None,  # identified by low saturation instead
    "yellow": [(20, 35)],
    "orange": [(5, 19)],
    "red": [(0, 4), (170, 179)],
    "green": [(45, 85)],
    "blue": [(95, 130)],
}

MIN_REGION_FRACTION = 0.002  # ignore colour blobs smaller than this share of the frame


@dataclass
class ObjectState:
    """What was seen: where it is, what colours it has, and what we think it is."""

    concept: str = ""
    confidence: float = 0.0
    colors: list[str] = field(default_factory=list)
    bbox: tuple[int, int, int, int] | None = None
    scramble: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def state_known(self) -> bool:
        return self.scramble is not None

    def __str__(self) -> str:
        head = f"{self.concept or 'unknown object'} (confidence {self.confidence:.2f})"
        colors = f"  colours: {', '.join(self.colors) or 'none found'}"
        state = f"  state  : {self.scramble if self.state_known else 'not readable from video'}"
        return "\n".join(
            [head, colors, state, *[f"  note   : {n}" for n in self.notes]]
        )


def available() -> bool:
    """True when OpenCV is installed. Callers degrade rather than crash."""
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return True


def detect_object(frames: list[Path]) -> ObjectState:
    """Identify the object in a set of frames from its colour makeup."""
    if not available():
        return ObjectState(notes=["opencv is not installed; cannot look at frames"])
    if not frames:
        return ObjectState(notes=["no frames given"])

    import cv2
    import numpy as np

    found: set[str] = set()
    boxes: list[tuple[int, int, int, int]] = []

    for path in frames:
        image = cv2.imread(str(path))
        if image is None:
            continue
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        area = image.shape[0] * image.shape[1]
        mask_total = np.zeros(hsv.shape[:2], dtype=np.uint8)

        for name in CUBE_HUES:
            mask = _color_mask(hsv, name, cv2, np)
            if mask.sum() / 255 > area * MIN_REGION_FRACTION:
                found.add(name)
                mask_total = cv2.bitwise_or(mask_total, mask)

        box = _bounding_box(mask_total, cv2)
        if box:
            boxes.append(box)

    state = ObjectState(colors=sorted(found), bbox=_median_box(boxes))
    # Six saturated colours in one object is a strong signal for a cube; this is
    # a recogniser, not a classifier, so it says so plainly.
    cube_colors = found & {"white", "yellow", "orange", "red", "green", "blue"}
    state.confidence = len(cube_colors) / 6.0
    if state.confidence >= 0.66:
        state.concept = "rubiks_cube"
    state.notes.append(
        f"{len(cube_colors)}/6 cube colours present across {len(frames)} frames"
    )
    return state


def read_state(frames: list[Path], concept: str = "") -> ObjectState:
    """Try to read the object's exact state. Honest about not managing it."""
    state = detect_object(frames)
    if concept:
        state.concept = concept
    if state.concept == "rubiks_cube":
        state.notes.append(
            "facelet reading is not implemented: a single view never shows all six "
            "faces, so supply the scramble with --scramble"
        )
    return state


def extract_frames(
    video: Path, out_dir: Path, fps: float = 4.0, limit: int = 60
) -> list[Path]:
    """Pull frames out of a video with ffmpeg, returning the ones written."""
    import shutil
    import subprocess

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH; install it to read video")

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("frame_*.png"):
        stale.unlink()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            f"fps={fps}",
            "-frames:v",
            str(limit),
            str(out_dir / "frame_%04d.png"),
        ],
        check=True,
    )
    return sorted(out_dir.glob("frame_*.png"))


def _color_mask(hsv: Any, name: str, cv2: Any, np: Any) -> Any:
    """Pixels matching one named colour."""
    if name == "white":
        return cv2.inRange(hsv, (0, 0, 160), (179, 60, 255))  # pale = low saturation

    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in CUBE_HUES[name] or []:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, (low, 90, 60), (high, 255, 255)))
    return mask


def _bounding_box(mask: Any, cv2: Any) -> tuple[int, int, int, int] | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    return int(x), int(y), int(w), int(h)


def _median_box(
    boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int] | None:
    if not boxes:
        return None
    middle = sorted(boxes, key=lambda b: b[2] * b[3])[len(boxes) // 2]
    return middle
