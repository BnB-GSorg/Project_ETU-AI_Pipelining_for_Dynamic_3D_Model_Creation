#pragma once
/**
 * @file types.hpp
 * @brief Common types and definitions for ETU
 */

#include <cstdint>
#include <string>
#include <vector>
#include <array>
#include <memory>
#include <optional>
#include <expected>
#include <span>
#include <string_view>

namespace etu {

// ============================================================================
// Error Handling (C++23 std::expected)
// ============================================================================

/**
 * @brief Error codes for ETU operations
 */
enum class ErrorCode : uint32_t {
    Success = 0,
    NotInitialized,
    InvalidArgument,
    OutOfMemory,
    FileNotFound,
    IOError,
    RendererError,
    GPUError,
    PipelineError,
    ShaderCompilationFailed,
    UnsupportedOperation,
    Unknown = 0xFFFFFFFF
};

/**
 * @brief Detailed error information
 */
struct Error {
    ErrorCode code;
    std::string message;
    std::string location; // __FILE__:__LINE__ where error occurred
    
    [[nodiscard]] constexpr bool is_success() const noexcept { 
        return code == ErrorCode::Success; 
    }
    
    [[nodiscard]] constexpr explicit operator bool() const noexcept { 
        return !is_success(); 
    }
};

/**
 * @brief Result type using C++23 std::expected
 */
template<typename T>
using Result = std::expected<T, Error>;

/**
 * @brief Result type for operations that don't return a value
 */
using Status = std::expected<void, Error>;

// ============================================================================
// Rendering Backend
// ============================================================================

/**
 * @brief Available rendering backends
 */
enum class RendererBackend : uint8_t {
    None = 0,
    OpenGL,     // Cross-platform fallback
    Vulkan,     // Modern cross-platform
    DirectX12,  // Windows
    Metal       // macOS/iOS
};

/**
 * @brief Convert renderer backend to string
 */
[[nodiscard]] constexpr std::string_view to_string(RendererBackend backend) noexcept {
    switch (backend) {
        case RendererBackend::OpenGL:    return "OpenGL";
        case RendererBackend::Vulkan:    return "Vulkan";
        case RendererBackend::DirectX12: return "DirectX 12";
        case RendererBackend::Metal:     return "Metal";
        default:                         return "None";
    }
}

// ============================================================================
// GPU Capabilities
// ============================================================================

/**
 * @brief GPU compute backend
 */
enum class GPUComputeBackend : uint8_t {
    None = 0,
    CUDA,           // NVIDIA
    MetalCompute,   // Apple
    VulkanCompute,  // Cross-platform
    DirectCompute   // Windows
};

/**
 * @brief GPU capabilities and device info
 */
struct GPUCapabilities {
    bool available = false;
    GPUComputeBackend compute_backend = GPUComputeBackend::None;
    std::string device_name;
    size_t total_memory = 0;        // bytes
    size_t available_memory = 0;    // bytes
    uint32_t compute_units = 0;
    bool supports_fp16 = false;
    bool supports_fp64 = false;
    bool supports_tensor_cores = false; // NVIDIA specific
    bool supports_ray_tracing = false;
};

// ============================================================================
// Configuration
// ============================================================================

/**
 * @brief Library configuration
 */
struct Config {
    RendererBackend preferred_renderer = RendererBackend::None; // Auto-detect
    bool enable_gpu_acceleration = true;
    bool enable_validation = true;  // Debug validation layers
    bool enable_profiling = false;
    std::string log_file;           // Empty = stdout
    uint32_t thread_count = 0;      // 0 = auto-detect
};

// ============================================================================
// Math Types (Simplified - replace with GLM/Eigen in production)
// ============================================================================

struct Vec2 {
    float x = 0, y = 0;
    constexpr Vec2() = default;
    constexpr Vec2(float x_, float y_) : x(x_), y(y_) {}
};

struct Vec3 {
    float x = 0, y = 0, z = 0;
    constexpr Vec3() = default;
    constexpr Vec3(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}
};

struct Vec4 {
    float x = 0, y = 0, z = 0, w = 0;
    constexpr Vec4() = default;
    constexpr Vec4(float x_, float y_, float z_, float w_) : x(x_), y(y_), z(z_), w(w_) {}
};

struct Mat4 {
    std::array<float, 16> data = {
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1
    }; // Identity matrix (column-major)
    
    [[nodiscard]] static constexpr Mat4 identity() noexcept { return {}; }
};

// ============================================================================
// 3D Model Types
// ============================================================================

/**
 * @brief Vertex data for 3D models
 */
struct Vertex {
    Vec3 position;
    Vec3 normal;
    Vec2 texcoord;
    Vec4 color = {1, 1, 1, 1};
};

/**
 * @brief Mesh data
 */
struct Mesh {
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;
    std::string name;
    uint32_t material_id = 0;
};

/**
 * @brief 3D Model composed of meshes
 */
struct Model {
    std::vector<Mesh> meshes;
    std::string name;
    Vec3 bounding_min;
    Vec3 bounding_max;
};

// ============================================================================
// Smart Pointers
// ============================================================================

template<typename T>
using Unique = std::unique_ptr<T>;

template<typename T>
using Shared = std::shared_ptr<T>;

template<typename T>
using Weak = std::weak_ptr<T>;

template<typename T, typename... Args>
[[nodiscard]] Unique<T> make_unique(Args&&... args) {
    return std::make_unique<T>(std::forward<Args>(args)...);
}

template<typename T, typename... Args>
[[nodiscard]] Shared<T> make_shared(Args&&... args) {
    return std::make_shared<T>(std::forward<Args>(args)...);
}

} // namespace etu
