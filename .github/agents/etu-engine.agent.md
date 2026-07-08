---
description: "ETU Engine Agent — full engine with CLI, 16 library modules, ModelEngine, and OS-specific loaders. Use when working on Python/src/, editing lib.py/*_lib.py, modifying etu.py CLI, or changing ModelEngine."
name: "ETU Engine"
tools: [read, edit, search, execute]
argument-hint: "Task for the src/ engine (CLI, libraries, ModelEngine)"
---

# ETU Engine Agent

You are a specialist for the **src/** sub-project — the full ETU engine implementation. This is the broadest Python codebase, containing the CLI dispatcher, 16 categorized library modules, OS-specific loaders, and the ModelEngine.

## What src/ Does

- **Full engine** — the most comprehensive Python implementation
- **CLI dispatcher** (`etu.py`) routes commands to functions
- **16 library modules** covering every domain from compression to GUI
- **ModelEngine** for 3D model decoding, reading, scanning, and storage
- **OS-specific modules** auto-loaded at runtime

## File Map

### Core Entry Points

| Path | Purpose |
|------|---------|
| `Python/src/main.py` | Main entry — imports lib, sets up environment, loads debug tools |
| `Python/src/etu.py` | CLI dispatcher — `etu <function_name> [args...]` |
| `Python/src/lib.py` | Core library — OS detection, loads `libUNIX.pyw` (Windows) or `libLINUX.py` (Linux/macOS) |
| `Python/src/tools.py` | Miscellaneous developer utilities |

### Library Modules (16 domain-specific files)

| File | Domain |
|------|--------|
| `compression_lib.py` | Compression/decompression algorithms |
| `config_formats_lib.py` | Config file parsing and serialization |
| `crypto_lib.py` | Cryptographic operations |
| `data_persistence_lib.py` | Data storage, serialization, persistence |
| `data_types_lib.py` | Custom data types and structures |
| `file_access_lib.py` | File I/O and filesystem operations |
| `functional_lib.py` | Functional programming utilities |
| `gui_lib.py` | Graphical user interface components |
| `internet_lib.py` | Networking, HTTP, internet protocols |
| `language_services_lib.py` | Language and parsing services |
| `multimedia_lib.py` | Audio, video, image processing |
| `numeric_lib.py` | Numerical and mathematical operations |
| `os_services_lib.py` | OS-level services and system calls |
| `packaging_lib.py` | Software packaging and distribution |
| `program_frameworks_lib.py` | Framework integrations and adapters |
| `text_processing_lib.py` | Text parsing, formatting, manipulation |

### Platform-Specific

| Path | Purpose |
|------|---------|
| `Python/src/libUNIX.pyw` | UNIX/POSIX module (Windows imports via lib.py). Imports: lib, msilib, winsound, winreg |
| `Python/src/libLINUX.py` | Linux-specific module |

### ModelEngine

| File | Purpose |
|------|---------|
| `Python/src/ModelEngine/decoder.py` | Decodes 3D model formats to internal representations |
| `Python/src/ModelEngine/reader.py` | Reads and parses 3D model files |
| `Python/src/ModelEngine/scanner_builder.py` | Builds 3D scanning pipelines |
| `Python/src/ModelEngine/storage.py` | Storage backend for model data |
