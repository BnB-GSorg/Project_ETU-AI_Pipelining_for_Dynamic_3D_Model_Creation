#pragma once
/**
 * @file etu.hpp
 * @brief Main header for ETU - AI Pipelining for Dynamic 3D Model Creation
 * 
 * Include this header to access all ETU functionality.
 */

#include "etu/types.hpp"
#include "etu/pipeline.hpp"
#include "etu/renderer.hpp"
#include "etu/gpu_context.hpp"

namespace etu {

/**
 * @brief Library version information
 */
constexpr struct Version {
    int major = 0;
    int minor = 1;
    int patch = 0;
    const char* string = "0.1.0";
} version;

/**
 * @brief Initialize the ETU library
 * @param config Optional configuration settings
 * @return true if initialization succeeded
 */
[[nodiscard]] bool initialize(const Config& config = {});

/**
 * @brief Shutdown the ETU library and release resources
 */
void shutdown();

/**
 * @brief Check if the library is initialized
 */
[[nodiscard]] bool is_initialized() noexcept;

/**
 * @brief Get the active rendering backend
 */
[[nodiscard]] RendererBackend get_active_renderer() noexcept;

/**
 * @brief Get GPU acceleration status
 */
[[nodiscard]] GPUCapabilities get_gpu_capabilities() noexcept;

} // namespace etu
