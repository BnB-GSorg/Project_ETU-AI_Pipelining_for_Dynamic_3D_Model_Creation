# Project Setup Manual

This manual walks through setting up the ETU repository from a clean machine, for both the Python demo and the C++ core.

---

## 1. Prerequisites

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| Python | 3.10+ | Demo pipeline |
| CMake | 3.25+ | C++ build system |
| C++ Compiler | C++23-capable (GCC 13+, Clang 16+, MSVC 19.34+) | Core implementation |
| Git | Any recent | Version control |

### Platform-Specific Toolchain Setup

#### macOS
```bash
# Xcode Command Line Tools (provides Clang)
xcode-select --install

# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# CMake + Python
brew install cmake python@3.12

# Optional: newer LLVM/Clang with full C++23 support
brew install llvm
```

#### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y build-essential cmake python3 python3-venv python3-pip

# GCC 13+ (for full C++23 support)
sudo apt install -y gcc-13 g++-13
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 100
```

#### Linux (Arch)
```bash
sudo pacman -S --noconfirm base-devel cmake python
```

#### Windows
1. Install **Visual Studio 2022** (Community or higher) with the **"Desktop development with C++"** workload.
2. Ensure the **Windows 10/11 SDK** is selected during install.
3. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add python.exe to PATH").
4. Install [CMake](https://cmake.org/download/) or use the one bundled with VS 2022.

> See [Compile-Guide](Compile-Guide.md) for detailed Windows/VS2022 build instructions.

---

## 2. Clone the Repository

```bash
git clone https://github.com/BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation.git
cd Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation
```

---

## 3. Set Up the Python Demo

```bash
cd demo

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows (cmd/PowerShell)

# Install package in editable mode
pip install -e .

# Optional: dev tools (pytest, black, ruff, mypy)
pip install -e ".[dev]"

# Optional: visualization tools
pip install -e ".[viz]"
```

### Verify

```bash
etu-demo --version
pytest
```

Expected: version string prints, and all tests pass (`pytest` should report `X passed`).

---

## 4. Set Up the C++ Core

```bash
cd src

# Configure (macOS/Linux)
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Configure (Windows, VS 2022)
cmake -B build -G "Visual Studio 17 2022"

# Build
cmake --build build --config Release
```

### Verify

```bash
# macOS/Linux
./build/etu_tests
./build/etu_app --help

# Windows
build\Release\etu_tests.exe
build\Release\etu_app.exe --help
```

Expected: all unit tests print `PASSED`, and `--help` shows usage text.

See [Compile-Guide](Compile-Guide.md) for renderer/GPU-specific CMake flags.

---

## 5. Set Up the Files Database

The `files/` directory ships with an empty structure:

```
files/
├── index.json     # Already present — database index
├── assets/        # Empty (add your input files here)
├── cache/         # Empty (auto-populated)
└── exports/       # Empty (auto-populated)
```

No setup required — just start adding assets. See [`files/README.md`](../../files/README.md) and [`files/AGENTS.md`](../../files/AGENTS.md) for schema details.

---

## 6. Editor Setup (Recommended)

### Zed / VS Code
- Both editors will pick up `.editorconfig` automatically for consistent indentation.
- For C++ IntelliSense, ensure `compile_commands.json` is generated:
  ```bash
  cmake -B src/build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  ```
  This file is already enabled by default in `src/CMakeLists.txt`.

### Recommended Extensions
| Editor | Extension |
|--------|-----------|
| VS Code | C/C++ (ms-vscode.cpptools), CMake Tools, Python, Ruff |
| Zed | Built-in LSP support for C++ (clangd) and Python (pyright) |

---

## 7. Environment Variables

Copy and customize if the project introduces a `.env` file:

```bash
# Example values (adjust as needed)
ETU_DEVICE=auto          # auto | cpu | cuda | mps
ETU_CACHE_DIR=../files/cache
ETU_LOG_LEVEL=INFO
```

---

## 8. Troubleshooting First Steps

| Problem | Check |
|---------|-------|
| `cmake` not found | Reinstall CMake, ensure it's on `PATH` |
| C++23 features fail to compile | Compiler too old — see minimum versions above |
| `pip install -e .` fails | Ensure Python 3.10+ and venv is activated |
| Renderer not detected | See [Compile-Guide](Compile-Guide.md) § Renderer Detection |
| GPU not detected | See `demo/.agents/skills/debug` or `src/AGENTS.md` § GPU |

For deeper issues, use the debugging skills in `demo/.agents/skills/debug/SKILL.md` and `files/.agents/skills/debug/SKILL.md`.

---

## 9. Next Steps

- Read [Development-Guide](Development-Guide.md) for coding standards and workflow.
- Read [Skills-Guide](Skills-Guide.md) to understand available agent skills.
- Read [Reference](Reference.md) for the full API surface.
