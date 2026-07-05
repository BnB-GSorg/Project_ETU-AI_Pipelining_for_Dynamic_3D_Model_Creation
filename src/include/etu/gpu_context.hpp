#pragma once
/**
 * @file gpu_context.hpp
 * @brief GPU compute context for acceleration
 * 
 * Supports: CUDA (NVIDIA), Metal Compute (Apple), Vulkan Compute, DirectCompute
 */

#include "etu/types.hpp"
#include <span>

namespace etu {

// ============================================================================
// GPU Buffer Types
// ============================================================================

/**
 * @brief GPU buffer usage flags
 */
enum class BufferUsage : uint32_t {
    None        = 0,
    Vertex      = 1 << 0,
    Index       = 1 << 1,
    Uniform     = 1 << 2,
    Storage     = 1 << 3,   // Shader storage / structured buffer
    Transfer    = 1 << 4,   // Staging buffer for transfers
    Indirect    = 1 << 5    // Indirect dispatch/draw commands
};

inline BufferUsage operator|(BufferUsage a, BufferUsage b) {
    return static_cast<BufferUsage>(static_cast<uint32_t>(a) | static_cast<uint32_t>(b));
}

inline BufferUsage operator&(BufferUsage a, BufferUsage b) {
    return static_cast<BufferUsage>(static_cast<uint32_t>(a) & static_cast<uint32_t>(b));
}

/**
 * @brief Memory location hint
 */
enum class MemoryLocation : uint8_t {
    DeviceLocal,    // GPU memory (fastest for GPU access)
    HostVisible,    // CPU-visible, GPU-accessible (for transfers)
    HostCached      // CPU-cached (best for readback)
};

// ============================================================================
// GPU Buffer
// ============================================================================

/**
 * @brief Handle to a GPU buffer
 */
class GPUBuffer {
public:
    GPUBuffer() = default;
    ~GPUBuffer();
    
    GPUBuffer(const GPUBuffer&) = delete;
    GPUBuffer& operator=(const GPUBuffer&) = delete;
    GPUBuffer(GPUBuffer&&) noexcept;
    GPUBuffer& operator=(GPUBuffer&&) noexcept;
    
    [[nodiscard]] bool valid() const noexcept;
    [[nodiscard]] size_t size() const noexcept;
    [[nodiscard]] BufferUsage usage() const noexcept;
    
    /**
     * @brief Map buffer to CPU memory (only for HostVisible buffers)
     */
    [[nodiscard]] Result<void*> map();
    
    /**
     * @brief Unmap previously mapped buffer
     */
    void unmap();

private:
    friend class GPUContext;
    struct Impl;
    Unique<Impl> pimpl_;
};

// ============================================================================
// Compute Shader
// ============================================================================

/**
 * @brief Handle to a compiled compute shader
 */
class ComputeShader {
public:
    ComputeShader() = default;
    ~ComputeShader();
    
    ComputeShader(const ComputeShader&) = delete;
    ComputeShader& operator=(const ComputeShader&) = delete;
    ComputeShader(ComputeShader&&) noexcept;
    ComputeShader& operator=(ComputeShader&&) noexcept;
    
    [[nodiscard]] bool valid() const noexcept;
    [[nodiscard]] std::string_view name() const noexcept;

private:
    friend class GPUContext;
    struct Impl;
    Unique<Impl> pimpl_;
};

// ============================================================================
// GPU Context
// ============================================================================

/**
 * @brief GPU compute context for accelerated operations
 */
class GPUContext {
public:
    GPUContext();
    ~GPUContext();
    
    GPUContext(const GPUContext&) = delete;
    GPUContext& operator=(const GPUContext&) = delete;
    GPUContext(GPUContext&&) noexcept;
    GPUContext& operator=(GPUContext&&) noexcept;
    
    /**
     * @brief Initialize GPU context
     * @param preferred_backend Preferred compute backend (None = auto-detect)
     */
    Status initialize(GPUComputeBackend preferred_backend = GPUComputeBackend::None);
    
    /**
     * @brief Shutdown and release resources
     */
    void shutdown();
    
    /**
     * @brief Check if GPU is available
     */
    [[nodiscard]] bool is_available() const noexcept;
    
    /**
     * @brief Get GPU capabilities
     */
    [[nodiscard]] GPUCapabilities capabilities() const noexcept;
    
    /**
     * @brief Get active compute backend
     */
    [[nodiscard]] GPUComputeBackend backend() const noexcept;
    
    // --- Buffer Management ---
    
    /**
     * @brief Create a GPU buffer
     */
    [[nodiscard]] Result<GPUBuffer> create_buffer(
        size_t size,
        BufferUsage usage,
        MemoryLocation location = MemoryLocation::DeviceLocal
    );
    
    /**
     * @brief Upload data to GPU buffer
     */
    Status upload_buffer(GPUBuffer& buffer, std::span<const std::byte> data, size_t offset = 0);
    
    /**
     * @brief Download data from GPU buffer
     */
    Status download_buffer(const GPUBuffer& buffer, std::span<std::byte> data, size_t offset = 0);
    
    // --- Compute Shaders ---
    
    /**
     * @brief Compile a compute shader from source
     * @param source Shader source code (HLSL, MSL, GLSL, or SPIR-V)
     * @param entry_point Entry point function name
     */
    [[nodiscard]] Result<ComputeShader> compile_shader(
        std::string_view source,
        std::string_view entry_point = "main"
    );
    
    /**
     * @brief Load a pre-compiled shader
     */
    [[nodiscard]] Result<ComputeShader> load_shader(std::span<const std::byte> bytecode);
    
    // --- Dispatch ---
    
    /**
     * @brief Dispatch a compute shader
     * @param shader Compute shader to dispatch
     * @param groups_x Number of thread groups in X
     * @param groups_y Number of thread groups in Y
     * @param groups_z Number of thread groups in Z
     */
    Status dispatch(
        const ComputeShader& shader,
        uint32_t groups_x,
        uint32_t groups_y = 1,
        uint32_t groups_z = 1
    );
    
    /**
     * @brief Wait for all GPU operations to complete
     */
    void synchronize();

private:
    struct Impl;
    Unique<Impl> pimpl_;
};

// ============================================================================
// Global GPU Context
// ============================================================================

/**
 * @brief Get the global GPU context (initialized by etu::initialize())
 */
[[nodiscard]] GPUContext* gpu_context() noexcept;

} // namespace etu
