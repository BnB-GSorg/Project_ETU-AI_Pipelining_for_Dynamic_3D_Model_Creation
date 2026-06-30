"""Gather *text* evidence from a 2D explainer for the (text-only) classifier.

Since DeepSeek can't see pixels, we convert the video into text signals:
  - a transcript (narration) — the richest, cheapest signal; pass an .srt/.vtt/.txt
  - optional OCR of keyframes (on-screen equations/labels) — needs pytesseract
  - any manual hint text

OCR is best-effort and optional; transcript alone already classifies well.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Evidence:
    transcript: str = ""
    ocr: str = ""
    hint: str = ""
    vision: str = ""        # description produced by the vision "eye" (hybrid path)

    def as_text(self) -> str:
        parts = []
        if self.hint:
            parts.append(f"[HINT]\n{self.hint}")
        if self.transcript:
            parts.append(f"[TRANSCRIPT]\n{self.transcript}")
        if self.vision:
            parts.append(f"[VISUAL DESCRIPTION]\n{self.vision}")
        if self.ocr:
            parts.append(f"[ON-SCREEN TEXT / OCR]\n{self.ocr}")
        return "\n\n".join(parts) if parts else "(no evidence provided)"


def _parse_captions(text: str) -> str:
    """Strip srt/vtt indices, timestamps and tags into plain narration."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s == "WEBVTT" or "-->" in s or s.isdigit():
            continue
        s = re.sub(r"<[^>]+>", "", s)        # drop <i>, <00:00:01.000> etc.
        if s:
            out.append(s)
    # collapse consecutive duplicates (common in auto-captions)
    deduped = [x for i, x in enumerate(out) if i == 0 or x != out[i - 1]]
    return " ".join(deduped)


def gather(transcript: Path | None = None, frames_dir: Path | None = None, hint: str = "") -> Evidence:
    ev = Evidence(hint=hint.strip())
    if transcript and transcript.exists():
        raw = transcript.read_text(encoding="utf-8", errors="ignore")
        ev.transcript = _parse_captions(raw) if transcript.suffix in (".srt", ".vtt") else raw.strip()
    if frames_dir and frames_dir.exists():
        ev.ocr = _ocr_frames(frames_dir)
    return ev


def _ocr_frames(frames_dir: Path, max_frames: int = 12) -> str:
    """Best-effort OCR of a few frames; silently no-op if pytesseract is absent."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    texts: list[str] = []
    frames = sorted(frames_dir.glob("*.png"))[:max_frames]
    for f in frames:
        try:
            t = pytesseract.image_to_string(Image.open(f)).strip()
            if t:
                texts.append(t)
        except Exception:
            continue
    seen, uniq = set(), []
    for line in " ".join(texts).split("\n"):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            uniq.append(line)
    return " ".join(uniq)
