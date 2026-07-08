# Python Module — Structure & Reference

This document describes the **Python module** of the ETU AI Pipelining for Dynamic 3D Model Creation project. It covers every top-level folder and essential file, explaining what each is responsible for and how they relate to one another.

---

## Directory Overview

```
Python/
├── .agents/                  # Copilot custom agent skills
├── demo/                     # Demonstration implementation (step-motion video)
├── MVP/                      # Theoretical-confirmation implementation (structured pipeline)
├── Project-ETU/              # Conda virtual environment source (Python 3.14 runtime)
├── src/                      # Full engine implementation (library + CLI + ModelEngine)
├── pyproject.toml            # Build configuration for the etu-demo package
└── Python.agent.md           # Agent instructions for the Python module
```

---

## Folder Details

### `.agents/`

**Purpose:** Copilot custom agent skills for the Python module.

Contains VS Code / GitHub Copilot agent skill definitions that assist with development tasks specific to this project. Currently houses a `skills/debug/` subfolder for debugging-related agent capabilities.

---

### `demo/`

**Purpose:** Demonstration — generates multiple 3D models and composes them into a step-motion video.

| Contents    | Description                                                                                                                                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py` | Single-file demo script. Uses a modified Open CASCADE engine to generate multiple 3D models and produce step-motion video output. Authored by MCHIGM. |

This is a lightweight, standalone demonstration — not a full pipeline. It exists to showcase visual results quickly without the overhead of the structured MVP pipeline.

---

### `MVP/`

**Purpose:** Theoretical confirmation — a structured, pip-installable package that implements the formal AI pipeline for 3D model creation.

| Contents                 | Description                                   |
| ------------------------ | --------------------------------------------- |
| `etu_demo/`            | Main Python package                           |
| `etu_demo/__init__.py` | Package exports                               |
| `etu_demo/main.py`     | CLI entry point (`etu-demo`)                |
| `etu_demo/pipeline.py` | Core pipeline logic with 6 stages (see below) |
| `etu_demo/utils.py`    | I/O helpers and utility functions             |
| `tests/`               | Unit tests (`test_pipeline.py`)             |
| `requirements.txt`     | Pip dependency fallback                       |
| `README.md`            | Quick-start guide for the MVP                 |

**Pipeline Stages (`Pipeline` enum):**

| Stage           | Description                      |
| --------------- | -------------------------------- |
| `INPUT`       | Load and validate input          |
| `PREPROCESS`  | Normalize, extract features      |
| `INFERENCE`   | Run AI model                     |
| `POSTPROCESS` | Generate mesh (marching cubes)   |
| `RENDERING`   | Compute normals, prepare buffers |
| `OUTPUT`      | Final model output               |

**Key Data Classes:**

- `PipelineConfig` — GPU toggle, quality, batch size, vertex/triangle limits
- `Model` — vertices, faces, normals, UVs as numpy arrays

The MVP is a **research/reference implementation** intended for rapid prototyping and theoretical validation. For production use, the C++ implementation (`../src/`) is preferred.

---

### `Project-ETU/`

**Purpose:** Conda virtual environment source — provides the Python 3.14 runtime used by `demo/`, `MVP/`, and `src/`.

This is a **bundled conda environment** containing:

- `python.exe` / `pythonw.exe` — Python 3.14 interpreter
- `DLLs/`, `Lib/`, `Library/` — Standard library and compiled extensions
- `Scripts/` — Installed CLI tools (pip, etc.)
- `conda-meta/` — Conda package metadata
- `include/` — C header files for the Python C API
- `share/`, `Tools/` — Supplementary tooling

It is **not source code** — it is the runtime environment that powers all three Python sub-projects (`demo`, `MVP`, `src`).

---

### `src/`

**Purpose:** Full ETU engine implementation — the main Python library, CLI dispatcher, and the ModelEngine for 3D model processing. This is a **separate implementation** from the MVP.

#### Core Entry Points

| File        | Description                                                                                                                                          |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py` | Main entry point. Imports`lib`, sets up the environment, and loads debugging tools. Authored by MCHIGM.                                            |
| `etu.py`  | CLI dispatcher. Usage:`etu <function_name> [args...]`. Routes function names to callables in the global namespace.                                 |
| `lib.py`  | Core library. Detects the OS at runtime and imports the appropriate OS-specific module (`libUNIX.pyw` on Windows, `libLINUX.py` on Linux/macOS). |

#### Categorized Library Modules

Each `*_lib.py` file encapsulates a domain of functionality:

| Module                        | Domain                                       |
| ----------------------------- | -------------------------------------------- |
| `compression_lib.py`        | Compression and decompression algorithms     |
| `config_formats_lib.py`     | Configuration file parsing and serialization |
| `crypto_lib.py`             | Cryptographic operations                     |
| `data_persistence_lib.py`   | Data storage, serialization, and persistence |
| `data_types_lib.py`         | Custom data types and structures             |
| `file_access_lib.py`        | File I/O and filesystem operations           |
| `functional_lib.py`         | Functional programming utilities             |
| `gui_lib.py`                | Graphical user interface components          |
| `internet_lib.py`           | Networking, HTTP, and internet protocols     |
| `language_services_lib.py`  | Language/parsing services                    |
| `multimedia_lib.py`         | Audio, video, and image processing           |
| `numeric_lib.py`            | Numerical and mathematical operations        |
| `os_services_lib.py`        | OS-level services and system calls           |
| `packaging_lib.py`          | Software packaging and distribution          |
| `program_frameworks_lib.py` | Framework integrations and adapters          |
| `text_processing_lib.py`    | Text parsing, formatting, and manipulation   |
| `tools.py`                  | Miscellaneous developer utilities            |

#### Platform-Specific Modules

| File            | Description                                                            |
| --------------- | ---------------------------------------------------------------------- |
| `libUNIX.pyw` | UNIX/POSIX-specific library module (imported on Windows via`lib.py`) |
| `libLINUX.py` | Linux-specific library module                                          |

#### ModelEngine

| File                   | Description                                            |
| ---------------------- | ------------------------------------------------------ |
| `decoder.py`         | Decodes 3D model formats into internal representations |
| `reader.py`          | Reads and parses 3D model files                        |
| `scanner_builder.py` | Builds 3D scanning pipelines                           |
| `storage.py`         | Storage backend for model data                         |

#### Other

| Path                   | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| `etu_demo.egg-info/` | Package metadata generated by`pip install -e .`        |
| `resources/`         | Reserved for assets and resource files (currently empty) |

---

## Root-Level Files

### `pyproject.toml`

Build configuration for the `etu-demo` package (v0.1.0). Defines:

- **Build system:** setuptools + wheel
- **Core dependencies:** numpy, torch, trimesh, pillow, tqdm
- **Dev dependencies:** pytest, black, ruff, mypy
- **Viz dependencies:** matplotlib, open3d, pyglet
- **Python:** ≥ 3.10

> ⚠️ **Note:** This file is pending update. Ignore for now.

### `Python.agent.md`

Agent instructions for the Python module. Provides coding guidelines (type hints, docstrings, dataclasses, NumPy preference, lazy imports, test coverage) and quick-reference commands for install, run, test, lint, format, and type-check workflows.

---

## Relationship Diagram

```
Project-ETU/ (conda venv — Python 3.14)
    ├── powers demo/       (demonstration: step-motion video, Open CASCADE)
    ├── powers MVP/        (theoretical confirmation: structured pipeline)
    └── powers src/        (full engine: CLI + libs + ModelEngine)

src/ (full engine)          MVP/ (reference pipeline)
    ├── main.py                 ├── etu_demo/main.py (CLI)
    ├── etu.py (CLI)            ├── etu_demo/pipeline.py (6-stage pipeline)
    ├── lib.py (OS loader)      └── etu_demo/utils.py (helpers)
    ├── *_lib.py (16 modules)
    ├── libUNIX.pyw / libLINUX.py
    └── ModelEngine/
```

- **`demo/`** and **`MVP/`** are independent implementations serving different purposes (demonstration vs. theoretical validation).
- **`src/`** is a third, separate implementation — the full engine with the broadest scope.
- All three share the **`Project-ETU/`** conda environment as their Python runtime.

---

*Last updated: 2026-07-08*
