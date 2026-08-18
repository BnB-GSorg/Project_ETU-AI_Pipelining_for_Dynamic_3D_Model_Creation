# Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation

<a href="https://arxiv.org/abs/2401.12345"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-AI Pipelining for Dynamic 3D Model Creation-b31b1b?logo=arxiv&logoColor=white" /></a>
[![PDF](https://img.shields.io/badge/Research_Gate-2401.12345-b31b1b.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/ELSEVIER-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/Scopus-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/Google_Scholar-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/IEEE-2401.12345-678910.svg)](LINK_TO_PAPER)
[![DOI](https://img.shields.io/badge/DOI-1234567890-blue.svg)](LINK_TO_DOI)
[![Conference](https://img.shields.io/badge/ICAIMS-2026-blue.svg)](https://enotice.mmsend.com/link.cfm?r=kvLsVn9rO4DWNSIMWcpnQA~~&pe=dUSyf-mtHzRGl6tKLycGSNHxvpkLf7C7Ur1JqH1_ums0yeIaO4AKl6ku18YU70Rxqc6KEkm2UcJcNKaQzlKbKA~~&t=ZYEqAxcGeKGqwNugwVaJFw~~)
[![Company name](https://img.shields.io/badge/github-BnB_Org-pink.svg)](https://github.com/BnB-GSorg)
[![GitHub REPO](https://img.shields.io/badge/github-MCHIGM.svg)](https://github.com/BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation)

This repository is the official implementation of the paper **"AI Pipelining for Dynamic 3D Model Creation"**, accepted at **IEEE ICAIMS 2026 / IEEE Xplore, 2026**.

---

## 🎯 What it does

Turn a flat 2D process video into an interactive 4D scene — 3D geometry plus
time — that you can orbit, scrub and slice.

Most explanatory content is trapped in 2D: a maths animation, a mechanical
walkthrough, a medical process diagram. Humans understand spatial processes
best in 3D. ETU reads a 2D video and re-authors it as a scene you can look at
from any angle, at any point in time. The output is a single scene file that a
viewer can load, play and cut through.

## 📌 Status

The engine is being **rewritten from scratch** in `src/`.

The previous implementation is retired. It was too complex to read and
maintain, so the rewrite prioritises simplicity: readable beats clever, and no
abstraction arrives before a second caller needs it.

Built so far: both scene formats, fully tested.

- **mmi-lite** (`etu/formats/scene.py`) — a scene as objects, each with a
  geometry (point cloud, box, surface, or line) and a sparse keyframe track;
  the viewer interpolates between keyframes (position/scale/opacity lerp,
  rotation slerp).
- **mmi-git v0.3** (`etu/formats/git.py`) — the same scene stored as an
  initial model, a chain of per-frame commits (a 4×4 pose delta per part),
  and a final model, so it plays back forward *and* backward without
  replaying from frame 0 every time. Reads v0.1/v0.2 files too.
- **Compiler** (`etu/formats/compiler.py`) — converts mmi-lite ⇄ mmi-git in
  both directions, carrying position, rotation, scale, and opacity.
- **Validator** (`etu/formats/validate.py`) — detects which of the two
  formats a file is from its own contents and validates accordingly.

Not yet built: the CV/LLM understanding pipeline, the CLI commands, and the
viewer — see `src/tests/` for what currently has coverage.

## 📁 Layout

```
Project-ETU/
├── src/                      # The engine — all development happens here
│   ├── main.py               #   entry point + command loop
│   ├── lib.py                #   utility helpers + file registry
│   ├── etu/
│   │   └── formats/
│   │       ├── scene.py      #   mmi-lite
│   │       ├── git.py        #   mmi-git v0.3
│   │       ├── compiler.py   #   mmi-lite <-> mmi-git
│   │       └── validate.py   #   format auto-detect + validation
│   └── tests/                #   pytest suite for the above
├── environment.yml           # Python dependency spec
├── AGENTS.md                 # Working agreement, also read by AI coding agents
└── README.md
```

A local `.env/` directory holds the built Python environment and editor
settings. It is not committed — `environment.yml` is all you need to rebuild.

## 🚀 Quick Start

### Python Engine

```bash
# Create the environment (once)
mamba env create --prefix .env/Python/etu -f environment.yml

# Run it
cd src
../.env/Python/etu/bin/python main.py           # interactive
../.env/Python/etu/bin/python main.py version   # one-shot command
```

Available commands: `help`, `files`, `version`, `exit`.

If mamba cannot write its package cache, prefix the create command with
`CONDA_PKGS_DIRS=.env/Python/.pkgs`.

### C++ Core

```bash
cd src

# macOS / Linux
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/etu_app

# Windows (Visual Studio 2022)
cmake -B build -G "Visual Studio 17 2022"
cmake --build build --config Release
build\Release\etu_app.exe
```

## 💻 Requirements

### C++ Core
- **C++23 compiler**: GCC 13+, Clang 16+, MSVC 19.34+ (VS 2022 17.4+)
- **CMake**: 3.25+
- **Graphics**: DirectX 12 (Win), Metal (Mac), Vulkan, or OpenGL

### Python Engine
- **Python**: 3.10+ (3.12 pinned in `environment.yml`)
- **Package manager**: mamba 2.x or conda 26.x
- **Dependencies**: numpy, pillow, wrapt — see `environment.yml`

## 🛠 Development

| Action | Command |
|--------|---------|
| Run | `cd src && ../.env/Python/etu/bin/python main.py` |
| Test | `.env/Python/etu/bin/pytest src/` |
| Lint | `.env/Python/etu/bin/ruff check src/` |
| Format | `BLACK_CACHE_DIR=/tmp/etu-black .env/Python/etu/bin/black src/` |
| Add a dependency | edit `environment.yml`, then `mamba env update --prefix .env/Python/etu -f environment.yml --prune` |

`environment.yml` is the single source of truth — never install packages ad hoc.

> **Note:** `black` needs `BLACK_CACHE_DIR` set to a short path on macOS when the
> repository lives under a long directory name, otherwise it aborts with
> `OSError: AF_UNIX path too long`.

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 📚 Citation

If you use this work in your research, please cite:

```bibtex
@inproceedings{etu2026,
  title={AI Pipelining for Dynamic 3D Model Creation},
  author={BnB .Org, Junming HUANG},
  booktitle={IEEE IICAIET},
  year={2026}
}
```

## 🤝 Continuous Development

Please read the AGENTS.md files in each directory for coding guidelines.

---

<table>
<tr>
  <td rowspan="2" valign="middle">
    <img alt="C/C++" src="https://img.shields.io/badge/C/C++-00599C?style=for-the-badge&logo=c&logoColor=white" /><br>
    <img alt="Python" src="https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  </td>
  <td align="center"><img height="60" alt="PyTorch" src="src/bin/pytorch.svg" /></td>
  <td align="center"><img height="60" alt="NumPy" src="src/bin/numpy.png" /></td>
  <td align="center"><img height="60" alt="SciPy" src="src/bin/scipy.svg" /></td>
  <td align="center"><img height="60" alt="SymPy" src="src/bin/sympy.png" /></td>
  <td align="center"><img height="60" alt="ONNX" src="src/bin/onnx.svg" /></td>
</tr>
<tr>
  <td align="center"><sub><b>PyTorch</b></sub></td>
  <td align="center"><sub><b>NumPy</b></sub></td>
  <td align="center"><sub><b>SciPy</b></sub></td>
  <td align="center"><sub><b>SymPy</b></sub></td>
  <td align="center"><sub><b>ONNX</b></sub></td>
</tr>
</table>
