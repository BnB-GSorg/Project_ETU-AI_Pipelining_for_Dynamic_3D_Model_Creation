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

The engine is **operation-driven**: it builds an exact model of a known object,
looks up what operations that object supports, turns a written instruction into
a sequence of them, and records each step as a commit.

```
video ──► vision ──► state ──┐
                             ├──► model ──► operations ──► commits ──► .mmi ──► viewer
text instruction ──► brain ──┘         ▲
                                 knowledge base
```

Built so far:

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
- **Knowledge base** (`etu/kb/`) — what an object is, what operations it
  supports, and what "finished" looks like. `rubiks.py` builds an exact 26‑cubie
  cube with correct face colours and knows what each of the 18 moves does.
- **Operations** (`etu/ops/`) — applies a move to the model and records it as a
  commit; runs a whole sequence and collects the chain.
- **Brain** (`etu/brain/`) — `plan.py` turns an instruction into operations
  (reading it literally, recognising an intent like "solve it", or asking a
  model that may only answer with catalogue moves); `llm.py` talks to seven
  providers through one `chat()`.
- **Vision** (`etu/vision/cv.py`) — deterministic OpenCV: finds the object and
  reads its colours to recognise the concept.
- **Viewer** (`viewer/`) — no-build Three.js: orbit, zoom, scrub, play forward
  and backward, toggle layers.

Not yet built: reading a full cube state from video (a single view never shows
all six faces, so the scramble is supplied instead), and a general solver —
today "solve" means undoing a known scramble.

## 📁 Layout

```
Project-ETU/
├── src/                      # The engine — all development happens here
│   ├── main.py               #   the command hub
│   ├── lib.py                #   shared paths, file registry, terminal I/O
│   ├── etu/
│   │   ├── model.py          #   a model: its parts and where they sit
│   │   ├── kb/               #   concepts, properties, operation catalogues
│   │   ├── ops/              #   apply operations, record commits
│   │   ├── brain/            #   instruction planning + LLM providers
│   │   ├── vision/           #   deterministic CV over video frames
│   │   └── formats/
│   │       ├── scene.py      #   mmi-lite
│   │       ├── git.py        #   mmi-git v0.3
│   │       ├── compiler.py   #   operations/mmi-lite -> mmi-git
│   │       └── validate.py   #   format auto-detect + validation
│   ├── viewer/               #   no-build Three.js player
│   └── tests/                #   pytest suite
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

# Watch the whole pipeline run, offline, with no API key
cd src
../.env/Python/etu/bin/python main.py demo

# Then view the result
../.env/Python/etu/bin/python main.py serve
# open the URL the demo printed
```

| Command | What it does |
|---------|--------------|
| `demo` | The whole pipeline: scramble a cube, solve it, compile it, validate it |
| `self-test` | Check everything works with no network and no API key |
| `search <text>` | What the knowledge base knows about a concept |
| `model <concept> --scramble "R U R'"` | Build a model and describe it |
| `instruct "solve it" --history "R U"` | Turn an instruction into operations |
| `execute --scramble S` | Run the operations, report the commits |
| `compile --scramble S --out f.mmi` | Write a compiled `.mmi` file |
| `validate <file>` | Check an mmi-lite or mmi-git file |
| `watch <video.mp4>` | Look at a video and identify the object |
| `serve` | Serve the project so the viewer can load files |

Also `help`, `files`, `version`, `exit`.

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
