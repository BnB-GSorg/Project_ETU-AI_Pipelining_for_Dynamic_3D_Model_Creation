---
description: "Guidelines for Python/demo/ — step-motion video with Open CASCADE engine. Use when editing main.py or adding demo features."
applyTo: "Python/demo/**"
---

# Demo Module Instructions

## Context
This is a lightweight standalone demonstration — single-file (`main.py`), generates multiple 3D models and composes them into a step-motion video using a modified Open CASCADE engine.

## Guidelines
- Keep it simple — single-file script, no complex abstractions
- Do not import from `Python/MVP/` or `Python/src/` — keep demo independent
- Do not modify `Python/Project-ETU/` — it is the Conda runtime, not source code
- Authored by MCHIGM — respect existing code style

## Run
```bash
python Python/demo/main.py
```
