# C++ Core Module - Agent Instructions

This directory contains the **C++ production implementation** of the ETU AI pipeline. It's designed for high performance, cross-platform support, and integration with graphics APIs.

## Quick Reference

| Action | Command (macOS/Linux) | Command (Windows) |
|--------|----------------------|-------------------|
| Configure | `cmake -B build -DCMAKE_BUILD_TYPE=Release` | `cmake -B build -G "Visual Studio 17 2022"` |
| Build | `cmake --build build` | `cmake --build build --config Release` |
| Test | `ctest --test-dir build` | `ctest --test-dir build -C Release` |
| Run | `./build/etu_app` | `build\Release\etu_app.exe` |

## Directory Structure

```
src/
├── CMakeLists.txt          # Build configuration
├── include/etu/            # Public headers
│   ├── etu.hpp             # Main include
│   ├── types.hpp           # Common types
│   ├── pipeline.hpp        # Pipeline interface
│   ├── renderer.hpp        # Renderer abstraction
│   └── gpu_context.hpp     # GPU compute context
├── src/                    # Implementation
│   ├── main.cpp            # Application entry
│   ├── etu.cpp             # Library init/shutdown
│   ├── pipeline.cpp        # Pipeline implementation
│   ├── renderer.cpp        # Renderer backends
│   └── gpu_context.cpp     # GPU abstraction
└── tests/
    └── test_main.cpp       # Unit tests
```

## Build Configuration

### CMake Options

| Option | Description | Default |
|--------|-------------|---------|
| `ETU_BUILD_TESTS` | Build unit tests | ON |
| `ETU_BUILD_EXAMPLES` | Build examples | ON |
| `ETU_ENABLE_GPU` | Enable GPU acceleration | ON |
| `ETU_USE_VULKAN` | Use Vulkan backend | OFF (auto) |
| `ETU_USE_DIRECTX` | Use DirectX 12 (Windows) | OFF (auto) |
| `ETU_USE_METAL` | Use Metal (macOS) | OFF (auto) |
| `ETU_USE_OPENGL` | Use OpenGL fallback | OFF (auto) |
| `ETU_AUTO_DETECT_RENDERER` | Auto-select best renderer | ON |

### Platform Auto-Detection

| Platform | Primary Renderer | GPU Compute |
|----------|-----------------|-------------|
| Windows | DirectX 12 | CUDA / DirectCompute |
| macOS | Metal | Metal Performance Shaders |
| Linux | Vulkan | CUDA / Vulkan Compute |

## C++23 Features Used

- `std::expected<T, E>` - Error handling
- `std::span<T>` - Non-owning views
- `std::string_view` - String views
- Designated initializers
- Concepts and constraints
- `constexpr` everywhere possible

## Key Components

### `etu::Pipeline`
Main processing class. Pimpl pattern for ABI stability.

```cpp
auto pipeline = etu::PipelineBuilder()
    .with_gpu(true)
    .with_quality(0.8f)
    .build();

auto result = pipeline->process(input_data);
if (result) {
    std::cout << result->name << std::endl;
} else {
    std::cerr << result.error().message << std::endl;
}
```

### `etu::IRenderer`
Abstract renderer interface. Implementations:
- `RendererDX12` - Windows DirectX 12
- `RendererMetal` - macOS Metal
- `RendererVulkan` - Cross-platform
- `RendererOpenGL` - Fallback

### `etu::GPUContext`
GPU compute abstraction for acceleration.

## Coding Standards

1. **C++23 required** - Use modern features
2. **RAII everywhere** - Use smart pointers
3. **`[[nodiscard]]`** - On functions returning values
4. **`noexcept`** - On non-throwing functions
5. **Pimpl pattern** - For ABI stability on public classes
6. **`std::expected`** - For error handling (no exceptions in hot paths)
7. **Const correctness** - Use `const` liberally

## File Naming

- Headers: `snake_case.hpp`
- Sources: `snake_case.cpp`
- Tests: `test_*.cpp`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE` or `kPascalCase`

## Adding New Renderer Backend

1. Create class inheriting `IRenderer`
2. Implement all virtual methods
3. Add to `create_renderer()` factory
4. Add CMake detection for dependencies
5. Update `get_available_backends()`

## Adding New Pipeline Stage

1. Add enum value to `PipelineStage`
2. Implement stage in `Pipeline::Impl::execute_pipeline()`
3. Report progress at start/end
4. Check `cancel_requested` for cancellation support
5. Add test case

## Visual Studio Setup

1. Install VS 2022 with "Desktop development with C++" workload
2. Ensure Windows SDK 10.0.22000+ installed
3. Configure with: `cmake -B build -G "Visual Studio 17 2022"`
4. Open `build/ETU.sln`
5. Set `etu_app` as startup project

## Dependencies

| Library | Purpose | Required |
|---------|---------|----------|
| Vulkan SDK | Vulkan rendering | Optional |
| DirectX 12 | Windows rendering | Windows only |
| Metal | macOS rendering | macOS only |
| CUDA Toolkit | GPU compute | Optional |
| OpenGL | Fallback renderer | Optional |

## Preprocessor Defines

| Define | Meaning |
|--------|---------|
| `ETU_HAS_VULKAN` | Vulkan available |
| `ETU_HAS_DIRECTX` | DirectX 12 available |
| `ETU_HAS_METAL` | Metal available |
| `ETU_HAS_OPENGL` | OpenGL available |
| `ETU_HAS_CUDA` | CUDA available |
| `ETU_HAS_MPS` | Metal Performance Shaders available |

## Performance Considerations

- Use `std::span` for function parameters to avoid copies
- Pre-allocate vectors with `.reserve()`
- Use move semantics for large objects
- Profile with platform-specific tools (Instruments, PIX, RenderDoc)
- GPU buffers: prefer device-local memory
