---
description: "Guidelines for Python/src/ — full engine with CLI, 16 lib modules, OS loaders, and ModelEngine. Use when editing etu.py, lib.py, *_lib.py, or ModelEngine/."
applyTo: "Python/src/**"
---

# Engine Module Instructions

## Context
Full ETU engine — the most comprehensive Python implementation. Contains the CLI dispatcher, 16 domain-specific library modules, OS-specific loaders, and the ModelEngine.

## Architecture

### Entry Flow
1. `main.py` → imports `lib.py` → sets up environment → loads debug tools
2. `lib.py` → detects OS → imports `libUNIX.pyw` (Windows) or `libLINUX.py` (Linux/macOS)
3. `etu.py` → CLI dispatcher: `etu <function_name> [args...]`

### Library Module Pattern
Each `*_lib.py` encapsulates one domain:
- `compression_lib.py` — compression algorithms
- `crypto_lib.py` — cryptography
- `gui_lib.py` — GUI components
- `numeric_lib.py` — math operations
- (See Python.md for the full 16-module table)

### ModelEngine
- `decoder.py` — decode 3D formats
- `reader.py` — parse 3D model files
- `scanner_builder.py` — build scanning pipelines
- `storage.py` — model data storage backend

## Constraints
- Do not modify `Python/Project-ETU/` — it is the Conda runtime
- Platform code: Windows → `libUNIX.pyw`, Linux/macOS → `libLINUX.py`
- Use `lib.install_from_OS()` for OS-specific module loading
- `Python/src/resources/` is reserved (currently empty)
