#pragma once
/**
 * @file renderer.hpp
 * @brief Cross-platform rendering abstraction
 * 
 * Supports: DirectX 12 (Windows), Metal (macOS), Vulkan, OpenGL (fallback)
 */

#include "etu/types.hpp"
#include <functional>

namespace etu {

// ============================================================================
// Renderer Configuration
// ============================================================================

/**
 * @brief Window/surface configuration for rendering
 */
struct RenderSurface {
    void* native_handle = nullptr;  // HWND (Win), NSView* (Mac), etc.
    uint32_t width = 1280;
    uint32_t height = 720;
    bool vsync = true;
    bool fullscreen = false;
    uint32_t msaa_samples = 4;      // 1 = no MSAA
};

/**
 * @brief Renderer configuration
 */
struct RendererConfig {
    RendererBackend backend = RendererBackend::None;  // Auto-detect
    RenderSurface surface;
    bool enable_debug_layer = true;
    bool enable_gpu_validation = false;
    uint32_t max_frames_in_flight = 2;
};

// ============================================================================
// Camera
// ============================================================================

/**
 * @brief Camera for 3D scene viewing
 */
struct Camera {
    Vec3 position = {0, 0, 5};
    Vec3 target = {0, 0, 0};
    Vec3 up = {0, 1, 0};
    float fov = 45.0f;          // degrees
    float near_plane = 0.1f;
    float far_plane = 1000.0f;
    
    [[nodiscard]] Mat4 view_matrix() const;
    [[nodiscard]] Mat4 projection_matrix(float aspect_ratio) const;
};

// ============================================================================
// Render Commands
// ============================================================================

/**
 * @brief Clear color for the render target
 */
struct ClearColor {
    float r = 0.1f, g = 0.1f, b = 0.1f, a = 1.0f;
};

// ============================================================================
// Renderer Interface
// ============================================================================

/**
 * @brief Abstract renderer interface
 * 
 * Concrete implementations:
 * - RendererDX12 (Windows)
 * - RendererMetal (macOS/iOS)  
 * - RendererVulkan (Cross-platform)
 * - RendererOpenGL (Fallback)
 */
class IRenderer {
public:
    virtual ~IRenderer() = default;
    
    /**
     * @brief Initialize the renderer
     */
    virtual Status initialize(const RendererConfig& config) = 0;
    
    /**
     * @brief Shutdown and release resources
     */
    virtual void shutdown() = 0;
    
    /**
     * @brief Get the active backend
     */
    [[nodiscard]] virtual RendererBackend backend() const noexcept = 0;
    
    /**
     * @brief Resize the render surface
     */
    virtual Status resize(uint32_t width, uint32_t height) = 0;
    
    /**
     * @brief Begin a new frame
     */
    virtual Status begin_frame() = 0;
    
    /**
     * @brief End the current frame and present
     */
    virtual Status end_frame() = 0;
    
    /**
     * @brief Clear the render target
     */
    virtual void clear(const ClearColor& color) = 0;
    
    /**
     * @brief Set the active camera
     */
    virtual void set_camera(const Camera& camera) = 0;
    
    /**
     * @brief Submit a model for rendering
     */
    virtual Status render_model(const Model& model, const Mat4& transform = Mat4::identity()) = 0;
    
    /**
     * @brief Wait for GPU to finish all work
     */
    virtual void wait_idle() = 0;
};

// ============================================================================
// Renderer Factory
// ============================================================================

/**
 * @brief Create a renderer with the specified backend
 * @param backend Desired backend (None = auto-detect best available)
 * @return Renderer instance or error
 */
[[nodiscard]] Result<Unique<IRenderer>> create_renderer(RendererBackend backend = RendererBackend::None);

/**
 * @brief Query available rendering backends on this system
 */
[[nodiscard]] std::vector<RendererBackend> get_available_backends();

/**
 * @brief Get the recommended backend for this system
 */
[[nodiscard]] RendererBackend get_recommended_backend();

} // namespace etu
