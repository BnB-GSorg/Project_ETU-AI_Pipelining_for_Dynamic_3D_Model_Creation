# Reference

Full API reference for the ETU Python demo (`demo/`) and C++ core (`src/`).

---

## Python Demo API (`etu_demo`)

Package: `demo/src/etu_demo/`

### `etu_demo.PipelineConfig`

```python
@dataclass
class PipelineConfig:
    use_gpu: bool = True
    batch_size: int = 1
    max_vertices: int = 1_000_000
    max_triangles: int = 500_000
    quality: float = 1.0              # 0.0 - 1.0
    enable_caching: bool = True
    cache_directory: Optional[Path] = None
```

### `etu_demo.PipelineStage`

```python
class PipelineStage(Enum):
    INPUT = auto()
    PREPROCESS = auto()
    INFERENCE = auto()
    POSTPROCESS = auto()
    RENDERING = auto()
    OUTPUT = auto()
```

### `etu_demo.pipeline.Model`

```python
@dataclass
class Model:
    vertices: np.ndarray             # (N, 3) float32
    faces: np.ndarray                # (M, 3) int32
    normals: Optional[np.ndarray]    # (N, 3) float32
    colors: Optional[np.ndarray]     # (N, 4) float32 RGBA
    uvs: Optional[np.ndarray]        # (N, 2) float32
    name: str = "generated_model"

    @property
    def num_vertices(self) -> int: ...
    @property
    def num_faces(self) -> int: ...
    def compute_normals(self) -> None: ...
```

### `etu_demo.Pipeline`

```python
class Pipeline:
    def __init__(self, config: Optional[PipelineConfig] = None): ...

    def set_progress_callback(
        self, callback: Callable[[PipelineStage, float, str], None]
    ) -> None: ...

    def process(self, input_path: Union[str, Path]) -> Model: ...
    def process_array(self, input_data: np.ndarray) -> Model: ...
    def cancel(self) -> None: ...

    @property
    def is_processing(self) -> bool: ...
    @property
    def device(self) -> str: ...   # "cpu" | "cuda" | "mps"
```

**Example:**
```python
from etu_demo import Pipeline, PipelineConfig

config = PipelineConfig(use_gpu=True, quality=0.8)
pipeline = Pipeline(config)
pipeline.set_progress_callback(lambda stage, progress, msg: print(stage, progress, msg))

model = pipeline.process("input.png")
print(model.num_vertices, model.num_faces)
```

### `etu_demo.utils`

```python
def load_input(path: Union[str, Path]) -> np.ndarray: ...
# Supports: .png .jpg .jpeg .bmp .tiff .tif .npy .npz .ply .pcd .xyz

def export_model(model, path: Union[str, Path], format: str = None) -> None: ...
# Supports: .obj .ply .stl .gltf .glb (+ trimesh-supported formats)

def create_grid(size: int = 64, spacing: float = 1.0) -> np.ndarray: ...
def normalize_vertices(vertices: np.ndarray, center: bool = True, scale: bool = True) -> np.ndarray: ...
```

### CLI (`etu-demo`)

```
etu-demo [options] <input_file>

Options:
  -o, --output <file>  Output file path (default: output.obj)
  --quality <0-1>       Quality level (default: 1.0)
  --no-gpu              Disable GPU acceleration
  --visualize           Show visualization of the result
  -v, --verbose         Enable verbose output
  --version             Show version
```

---

## C++ Core API (`etu`)

Headers: `src/include/etu/`

### `etu::Config` / Library Lifecycle (`etu.hpp`)

```cpp
struct Config {
    RendererBackend preferred_renderer = RendererBackend::None; // Auto-detect
    bool enable_gpu_acceleration = true;
    bool enable_validation = true;
    bool enable_profiling = false;
    std::string log_file;
    uint32_t thread_count = 0; // 0 = auto-detect
};

bool initialize(const Config& config = {});
void shutdown();
bool is_initialized() noexcept;
RendererBackend get_active_renderer() noexcept;
GPUCapabilities get_gpu_capabilities() noexcept;
```

### Core Types (`types.hpp`)

```cpp
enum class ErrorCode : uint32_t {
    Success, NotInitialized, InvalidArgument, OutOfMemory, FileNotFound,
    IOError, RendererError, GPUError, PipelineError,
    ShaderCompilationFailed, UnsupportedOperation, Unknown
};

struct Error {
    ErrorCode code;
    std::string message;
    std::string location;
    constexpr bool is_success() const noexcept;
    constexpr explicit operator bool() const noexcept;
};

template<typename T> using Result = std::expected<T, Error>;
using Status = std::expected<void, Error>;

enum class RendererBackend : uint8_t { None, OpenGL, Vulkan, DirectX12, Metal };
constexpr std::string_view to_string(RendererBackend backend) noexcept;

enum class GPUComputeBackend : uint8_t { None, CUDA, MetalCompute, VulkanCompute, DirectCompute };

struct GPUCapabilities {
    bool available = false;
    GPUComputeBackend compute_backend = GPUComputeBackend::None;
    std::string device_name;
    size_t total_memory = 0;
    size_t available_memory = 0;
    uint32_t compute_units = 0;
    bool supports_fp16 = false;
    bool supports_fp64 = false;
    bool supports_tensor_cores = false;
    bool supports_ray_tracing = false;
};

// Math types: Vec2, Vec3, Vec4, Mat4 (identity() static factory)

struct Vertex { Vec3 position; Vec3 normal; Vec2 texcoord; Vec4 color; };
struct Mesh { std::vector<Vertex> vertices; std::vector<uint32_t> indices; std::string name; uint32_t material_id; };
struct Model { std::vector<Mesh> meshes; std::string name; Vec3 bounding_min; Vec3 bounding_max; };

template<typename T> using Unique = std::unique_ptr<T>;
template<typename T> using Shared = std::shared_ptr<T>;
```

### Pipeline (`pipeline.hpp`)

```cpp
enum class PipelineStage : uint8_t {
    Input, Preprocess, Inference, PostProcess, Rendering, Output
};

struct StageResult {
    PipelineStage stage;
    bool success;
    double execution_time_ms;
    std::string message;
};

struct PipelineConfig {
    bool use_gpu = true;
    uint32_t batch_size = 1;
    uint32_t max_vertices = 1'000'000;
    uint32_t max_triangles = 500'000;
    float quality_level = 1.0f;
    bool enable_caching = true;
    std::string cache_directory;
};

class Pipeline {
public:
    using ProgressCallback = std::function<void(PipelineStage, float, std::string_view)>;

    Status configure(const PipelineConfig& config);
    const PipelineConfig& config() const noexcept;
    void set_progress_callback(ProgressCallback callback);

    Result<Model> process(std::span<const std::byte> input_data);
    std::future<Result<Model>> process_async(std::span<const std::byte> input_data);

    void cancel();
    bool is_processing() const noexcept;
    std::vector<StageResult> get_stage_results() const;
};

class PipelineBuilder {
public:
    PipelineBuilder& with_gpu(bool enable = true);
    PipelineBuilder& with_batch_size(uint32_t size);
    PipelineBuilder& with_quality(float level);
    PipelineBuilder& with_caching(bool enable, std::string_view cache_dir = "");
    PipelineBuilder& with_limits(uint32_t max_vertices, uint32_t max_triangles);
    Result<Pipeline> build();
};
```

**Example:**
```cpp
#include "etu/etu.hpp"

etu::initialize();

auto pipeline = etu::PipelineBuilder()
    .with_gpu(true)
    .with_quality(0.8f)
    .build();

if (pipeline) {
    pipeline->set_progress_callback([](auto stage, float progress, auto msg) {
        std::cout << static_cast<int>(stage) << ": " << progress << " " << msg << "\n";
    });

    std::vector<std::byte> input(1024);
    auto result = pipeline->process(input);
    if (result) {
        std::cout << "Model: " << result->name << "\n";
    }
}

etu::shutdown();
```

### Renderer (`renderer.hpp`)

```cpp
struct RenderSurface {
    void* native_handle = nullptr;
    uint32_t width = 1280, height = 720;
    bool vsync = true;
    bool fullscreen = false;
    uint32_t msaa_samples = 4;
};

struct RendererConfig {
    RendererBackend backend = RendererBackend::None;
    RenderSurface surface;
    bool enable_debug_layer = true;
    bool enable_gpu_validation = false;
    uint32_t max_frames_in_flight = 2;
};

struct Camera {
    Vec3 position = {0, 0, 5}, target = {0, 0, 0}, up = {0, 1, 0};
    float fov = 45.0f, near_plane = 0.1f, far_plane = 1000.0f;
    Mat4 view_matrix() const;
    Mat4 projection_matrix(float aspect_ratio) const;
};

struct ClearColor { float r = 0.1f, g = 0.1f, b = 0.1f, a = 1.0f; };

class IRenderer {
public:
    virtual Status initialize(const RendererConfig& config) = 0;
    virtual void shutdown() = 0;
    virtual RendererBackend backend() const noexcept = 0;
    virtual Status resize(uint32_t width, uint32_t height) = 0;
    virtual Status begin_frame() = 0;
    virtual Status end_frame() = 0;
    virtual void clear(const ClearColor& color) = 0;
    virtual void set_camera(const Camera& camera) = 0;
    virtual Status render_model(const Model& model, const Mat4& transform = Mat4::identity()) = 0;
    virtual void wait_idle() = 0;
};

Result<Unique<IRenderer>> create_renderer(RendererBackend backend = RendererBackend::None);
std::vector<RendererBackend> get_available_backends();
RendererBackend get_recommended_backend();
```

### GPU Context (`gpu_context.hpp`)

```cpp
enum class BufferUsage : uint32_t {
    None = 0, Vertex = 1<<0, Index = 1<<1, Uniform = 1<<2,
    Storage = 1<<3, Transfer = 1<<4, Indirect = 1<<5
};
enum class MemoryLocation : uint8_t { DeviceLocal, HostVisible, HostCached };

class GPUBuffer {
public:
    bool valid() const noexcept;
    size_t size() const noexcept;
    BufferUsage usage() const noexcept;
    Result<void*> map();
    void unmap();
};

class ComputeShader {
public:
    bool valid() const noexcept;
    std::string_view name() const noexcept;
};

class GPUContext {
public:
    Status initialize(GPUComputeBackend preferred_backend = GPUComputeBackend::None);
    void shutdown();
    bool is_available() const noexcept;
    GPUCapabilities capabilities() const noexcept;
    GPUComputeBackend backend() const noexcept;

    Result<GPUBuffer> create_buffer(size_t size, BufferUsage usage, MemoryLocation location = MemoryLocation::DeviceLocal);
    Status upload_buffer(GPUBuffer& buffer, std::span<const std::byte> data, size_t offset = 0);
    Status download_buffer(const GPUBuffer& buffer, std::span<std::byte> data, size_t offset = 0);

    Result<ComputeShader> compile_shader(std::string_view source, std::string_view entry_point = "main");
    Result<ComputeShader> load_shader(std::span<const std::byte> bytecode);

    Status dispatch(const ComputeShader& shader, uint32_t groups_x, uint32_t groups_y = 1, uint32_t groups_z = 1);
    void synchronize();
};

GPUContext* gpu_context() noexcept; // Global context, set by etu::initialize()
```

---

## Files Database Schema (`files/index.json`)

See [`files/README.md`](../../files/README.md) and [`files/AGENTS.md`](../../files/AGENTS.md) for the full schema. Summary:

```json
{
  "version": "1.0.0",
  "collections": {
    "assets":  { "path": "assets/",  "entries": [ /* id, name, type, format, size_bytes, created, tags, metadata */ ] },
    "cache":   { "path": "cache/",   "entries": [ /* id, source_id, type, created, expires, size_bytes */ ] },
    "exports": { "path": "exports/", "entries": [ /* id, name, format, source_assets, pipeline_config, created, size_bytes, vertices, faces */ ] }
  }
}
```

---

## CMake Build Options

See [Compile-Guide](Compile-Guide.md) § "CMake Configuration Options" for the full, authoritative list.

| Option | Default |
|--------|---------|
| `ETU_BUILD_TESTS` | `ON` |
| `ETU_BUILD_EXAMPLES` | `ON` |
| `ETU_ENABLE_GPU` | `ON` |
| `ETU_AUTO_DETECT_RENDERER` | `ON` |
| `ETU_USE_VULKAN` / `ETU_USE_DIRECTX` / `ETU_USE_METAL` / `ETU_USE_OPENGL` | `OFF` (auto-set) |

## Preprocessor Defines (C++)

| Define | Meaning |
|--------|---------|
| `ETU_HAS_VULKAN` | Vulkan available |
| `ETU_HAS_DIRECTX` | DirectX 12 available |
| `ETU_HAS_METAL` | Metal available |
| `ETU_HAS_OPENGL` | OpenGL available |
| `ETU_HAS_CUDA` | CUDA available |
| `ETU_HAS_MPS` | Metal Performance Shaders available |
