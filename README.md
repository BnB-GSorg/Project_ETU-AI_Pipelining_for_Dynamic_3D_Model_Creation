# Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation

<a href="https://arxiv.org/abs/2401.12345"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-AI Pipelining for Dynamic 3D Model Creation-b31b1b?logo=arxiv&logoColor=white" /></a>
[![PDF](https://img.shields.io/badge/Research_Gate-2401.12345-b31b1b.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/ELSEVIER-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/Scopus-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/Google_Scholar-2401.12345-orange.svg)](LINK_TO_PAPER)
[![Paper](https://img.shields.io/badge/IEEE-2401.12345-678910.svg)](LINK_TO_PAPER)
[![DOI:#DOINUMBER](https://zenodo.org/badge/DOI/1#DOINUMBER.svg)](https://doi.org/10.1007/#DOINUMBER)
[![Conference](https://img.shields.io/badge/IICAIET-2026-blue.svg)](https://enotice.mmsend.com/link.cfm?r=kvLsVn9rO4DWNSIMWcpnQA~~&pe=dUSyf-mtHzRGl6tKLycGSNHxvpkLf7C7Ur1JqH1_ums0yeIaO4AKl6ku18YU70Rxqc6KEkm2UcJcNKaQzlKbKA~~&t=ZYEqAxcGeKGqwNugwVaJFw~~)
[![Company name](https://img.shields.io/badge/github-BnB_Org-pink.svg)](https://github.com/BnB-GSorg)
[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/BnB-GSorg/Project_ETU-AI_Pipelining_for_Dynamic_3D_Model_Creation)

This repository is the official implementation of the paper **"AI Pipelining for Dynamic 3D Model Creation"**, accepted at **IEEE IICAIET 2026 / IEEE Xplore, 2026**.

---

## 📋 Overview

ETU (Efficient Topology Unfolding) is an AI-powered pipeline for dynamic 3D model creation. It combines deep learning with efficient mesh generation algorithms to produce high-quality 3D models from various inputs.

### Features

- 🚀 **High Performance** - C++23 core with GPU acceleration
- 🎨 **Cross-Platform Rendering** - DirectX 12, Metal, Vulkan, OpenGL
- 🐍 **Python Demo** - Rapid prototyping and research
- 📦 **Database-like File System** - Organized asset management

## 🗂️ Project Structure

```
Project-ETU/
├── demo/           # Python function implementation
│   ├── src/        #    Source code
│   └── tests/      #    Unit tests
├── src/            # 🔧 C++ core implementation
│   ├── include/    #    Public headers
│   ├── src/        #    Implementation
│   └── tests/      #    Unit tests
├── docs/           # 📚 Documentation
│   ├── wiki/       #    Wiki pages
│   └── materials/  #    Papers, slides, figures
└── files/          # 📦 File database
    ├── assets/     #    Input assets
    ├── cache/      #    Cached data
    └── exports/    #    Generated outputs
```

## 🚀 Quick Start

### Python Demo

```bash
cd demo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Run
etu-demo input.png -o output.obj
```

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

### Python Demo
- **Python**: 3.10+
- **Dependencies**: numpy, torch, trimesh, pillow

## 📖 Documentation

See [`docs/`](docs/) for detailed documentation:
- [Wiki](docs/wiki/) - Usage guides and tutorials
  - [Home](docs/wiki/Home.md) - Wiki index
  - [Project Setup Manual](docs/wiki/Project-Setup-Manual.md) - Set up the repo from scratch
  - [Compile Guide](docs/wiki/Compile-Guide.md) - Build the C++ core on macOS/Linux/Windows (VS 2022)
  - [Development Guide](docs/wiki/Development-Guide.md) - Coding standards, workflow, testing
  - [Skills Guide](docs/wiki/Skills-Guide.md) - How to use and extend agent skills
  - [Reference](docs/wiki/Reference.md) - Full Python + C++ API reference
- [Materials](docs/materials/) - Research papers and presentations

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
    <img src="https://img.shields.io/badge/C/C++-00599C?style=for-the-badge&logo=c&logoColor=white" /><br>
    <img src="https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  </td>
  <td align="center"><img height="60" src="files/assets/logos/pytorch.svg" /></td>
  <td align="center"><img height="60" src="files/assets/logos/numpy.png" /></td>
  <td align="center"><img height="60" src="files/assets/logos/scipy.svg" /></td>
  <td align="center"><img height="60" src="files/assets/logos/sympy.png" /></td>
  <td align="center"><img height="60" src="files/assets/logos/onnx.svg" /></td>
</tr>
<tr>
  <td align="center"><sub><b>PyTorch</b></sub></td>
  <td align="center"><sub><b>NumPy</b></sub></td>
  <td align="center"><sub><b>SciPy</b></sub></td>
  <td align="center"><sub><b>SymPy</b></sub></td>
  <td align="center"><sub><b>ONNX</b></sub></td>
</tr>
</table>
