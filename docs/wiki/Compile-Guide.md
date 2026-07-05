# Compile Guide

Detailed instructions for building the ETU C++ core (`src/`) across platforms, including rendering backend and GPU acceleration configuration.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| C++ Standard | C++23 (required) |
| CMake | 3.25+ |
| Compiler | GCC 13+, Clang 16+, or MSVC 19.34+ (VS 2022 17.4+) |

---

## 1. Basic Build (Any Platform)

```bash
cd src
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Outputs:
- `build/libetu_core.a` (or `.lib` on Windows) — static library
- `build/etu_app` (or `.exe`) — CLI application
- `build/etu_tests` (or `.exe`) — unit tests

---

## 2. Platform-Specific Instructions

### macOS

```bash
cd src
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(sysctl -n hw.ncpu)

./build/etu_tests
./build/etu_app --help
```

Auto-detected renderer: **Metal** (primary), **OpenGL** (fallback).
GPU acceleration: **Metal Performance Shaders** (if available).

### Linux

```bash
cd src
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

./build/etu_tests
./build/etu_app --help
```

Auto-detected renderer: **Vulkan** (primary, requires Vulkan SDK/loader), **OpenGL** (fallback).
GPU acceleration: **CUDA** (if NVIDIA toolkit is installed) or **Vulkan Compute**.

Install Vulkan SDK (Ubuntu example):
```bash
sudo apt install -y libvulkan-dev vulkan-tools
```

### Windows (Visual Studio 2022)

1. Open **"x64 Native Tools Command Prompt for VS 2022"** (or use PowerShell with VS environment loaded).
2. Configure and generate the solution:

```powershell
cd src
cmake -B build -G "Visual Studio 17 2022" -A x64
```

3. Build from command line:

```powershell
cmake --build build --config Release
```

   Or open `build\ETU.sln` in Visual Studio, set `etu_app` as the **Startup Project**, and press F5 / Ctrl+F5.

4. Run:

```powershell
build\Release\etu_tests.exe
build\Release\etu_app.exe --help
```

Auto-detected renderer: **DirectX 12** (primary), **OpenGL** (fallback).
GPU acceleration: **CUDA** (if installed) or **DirectCompute**.

#### Visual Studio 2022 Requirements Checklist

- [ ] Workload: **Desktop development with C++**
- [ ] Component: **MSVC v143 - VS 2022 C++ x64/x86 build tools**
- [ ] Component: **Windows 10/11 SDK** (latest)
- [ ] Component: **C++ CMake tools for Windows**
- [ ] (Optional) **C++ Clang Compiler for Windows** if you prefer clang-cl

---

## 3. CMake Configuration Options

Pass these with `-D<OPTION>=<ON|OFF>` during the configure step.

| Option | Description | Default |
|--------|-------------|---------|
| `ETU_BUILD_TESTS` | Build unit tests | `ON` |
| `ETU_BUILD_EXAMPLES` | Build example applications | `ON` |
| `ETU_ENABLE_GPU` | Enable GPU acceleration | `ON` |
| `ETU_AUTO_DETECT_RENDERER` | Auto-select best renderer for platform | `ON` |
| `ETU_USE_VULKAN` | Force Vulkan backend | `OFF` |
| `ETU_USE_DIRECTX` | Force DirectX 12 backend (Windows only) | `OFF` |
| `ETU_USE_METAL` | Force Metal backend (macOS only) | `OFF` |
| `ETU_USE_OPENGL` | Force OpenGL fallback | `OFF` |

### Examples

Force Vulkan on Linux even if auto-detect would pick something else:
```bash
cmake -B build -DETU_AUTO_DETECT_RENDERER=OFF -DETU_USE_VULKAN=ON -DETU_USE_OPENGL=ON
```

Disable GPU acceleration entirely (CPU-only build, useful for CI):
```bash
cmake -B build -DETU_ENABLE_GPU=OFF
```

Skip building tests (faster CI builds for release packaging):
```bash
cmake -B build -DETU_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release
```

---

## 4. Renderer Detection Logic

`CMakeLists.txt` auto-detects the platform and chooses a primary renderer + OpenGL fallback:

| Platform | Primary Renderer | Always-On Fallback |
|----------|-------------------|---------------------|
| Windows | DirectX 12 | OpenGL |
| macOS | Metal | OpenGL |
| Linux/Other | Vulkan | OpenGL |

This happens in the `ETU_AUTO_DETECT_RENDERER` block of `src/CMakeLists.txt`. Preprocessor defines are set accordingly:

```cpp
#if defined(ETU_HAS_METAL)
// Metal-specific code
#endif
#if defined(ETU_HAS_VULKAN)
// Vulkan-specific code
#endif
#if defined(ETU_HAS_DIRECTX)
// DirectX 12-specific code
#endif
#if defined(ETU_HAS_OPENGL)
// OpenGL-specific code
#endif
```

Check what was actually detected in the CMake configure log:
```
-- [ETU] Platform: Apple - Using Metal (primary)
-- [ETU] Metal enabled
-- [ETU] OpenGL found (fallback renderer)
```

---

## 5. GPU Acceleration Detection

GPU compute backends are detected independently of the renderer:

| Backend | Detected When |
|---------|---------------|
| CUDA | `check_language(CUDA)` finds `nvcc` |
| Metal Performance Shaders | `MetalPerformanceShaders.framework` found (macOS) |
| Vulkan Compute | Vulkan SDK present, used via `ETU_HAS_VULKAN` |
| DirectCompute | Bundled with DirectX 12 on Windows |

Preprocessor defines: `ETU_HAS_CUDA`, `ETU_HAS_MPS`.

Verify at runtime:
```bash
./build/etu_app
# Look for the "=== System Information ===" block:
#   Renderer: Metal
#   GPU: Apple GPU
```

---

## 6. Running Tests

```bash
# Via CTest
ctest --test-dir build --output-on-failure

# Or directly
./build/etu_tests          # macOS/Linux
build\Release\etu_tests.exe  # Windows
```

---

## 7. Clean Rebuild

```bash
rm -rf src/build            # macOS/Linux
rmdir /s /q src\build       # Windows

cmake -B src/build -DCMAKE_BUILD_TYPE=Release
cmake --build src/build
```

---

## 8. Common Build Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `error: 'expected' is not a member of 'std'` | Compiler too old for C++23 | Upgrade GCC/Clang/MSVC (see version table above) |
| `Vulkan_FOUND` is false | Vulkan SDK not installed | Install LunarG Vulkan SDK or `libvulkan-dev` |
| `d3d12.lib not found` | Not building on Windows or missing SDK | Install Windows SDK via VS Installer |
| `Metal.framework not found` | Building on non-Apple platform | Expected — Metal only builds on macOS |
| Linker errors on `libc++` (Clang) | Missing `-stdlib=libc++` | Already set in `CMakeLists.txt`; ensure LLVM is installed via Homebrew |
| CMake picks wrong compiler | Stale cache | Delete `build/` and reconfigure |

---

## 9. Cross-Compiling / CI Notes

- For headless CI (no GPU/display), use `-DETU_ENABLE_GPU=OFF` and let it fall back to OpenGL/CPU paths — `render_model` calls are still safe to invoke (they no-op without a live context in test builds).
- `CMAKE_EXPORT_COMPILE_COMMANDS=ON` is set by default, producing `build/compile_commands.json` for clangd/IDE integration.
