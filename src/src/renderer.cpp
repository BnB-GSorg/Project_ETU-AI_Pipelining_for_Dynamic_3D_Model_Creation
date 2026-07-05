/**
 * @file renderer.cpp
 * @brief Cross-platform renderer implementation
 */

#include "etu/renderer.hpp"
#include <cmath>

namespace etu {

// ============================================================================
// Camera Implementation
// ============================================================================

Mat4 Camera::view_matrix() const {
    // Simple look-at matrix calculation
    Vec3 f = { // forward (normalized)
        target.x - position.x,
        target.y - position.y,
        target.z - position.z
    };
    float len = std::sqrt(f.x*f.x + f.y*f.y + f.z*f.z);
    f.x /= len; f.y /= len; f.z /= len;
    
    // right = forward x up
    Vec3 r = {
        f.y * up.z - f.z * up.y,
        f.z * up.x - f.x * up.z,
        f.x * up.y - f.y * up.x
    };
    len = std::sqrt(r.x*r.x + r.y*r.y + r.z*r.z);
    r.x /= len; r.y /= len; r.z /= len;
    
    // recalculated up = right x forward
    Vec3 u = {
        r.y * f.z - r.z * f.y,
        r.z * f.x - r.x * f.z,
        r.x * f.y - r.y * f.x
    };
    
    Mat4 view;
    view.data = {
        r.x, u.x, -f.x, 0,
        r.y, u.y, -f.y, 0,
        r.z, u.z, -f.z, 0,
        -(r.x*position.x + r.y*position.y + r.z*position.z),
        -(u.x*position.x + u.y*position.y + u.z*position.z),
         (f.x*position.x + f.y*position.y + f.z*position.z),
        1
    };
    return view;
}

Mat4 Camera::projection_matrix(float aspect_ratio) const {
    float fov_rad = fov * 3.14159265358979323846f / 180.0f;
    float tan_half_fov = std::tan(fov_rad / 2.0f);
    
    Mat4 proj;
    proj.data = {
        1.0f / (aspect_ratio * tan_half_fov), 0, 0, 0,
        0, 1.0f / tan_half_fov, 0, 0,
        0, 0, -(far_plane + near_plane) / (far_plane - near_plane), -1,
        0, 0, -(2.0f * far_plane * near_plane) / (far_plane - near_plane), 0
    };
    return proj;
}

// ============================================================================
// Null Renderer (Stub Implementation)
// ============================================================================

class RendererNull : public IRenderer {
public:
    Status initialize(const RendererConfig&) override { return {}; }
    void shutdown() override {}
    RendererBackend backend() const noexcept override { return RendererBackend::None; }
    Status resize(uint32_t, uint32_t) override { return {}; }
    Status begin_frame() override { return {}; }
    Status end_frame() override { return {}; }
    void clear(const ClearColor&) override {}
    void set_camera(const Camera&) override {}
    Status render_model(const Model&, const Mat4&) override { return {}; }
    void wait_idle() override {}
};

// ============================================================================
// OpenGL Renderer (Fallback)
// ============================================================================

#if defined(ETU_HAS_OPENGL)
class RendererOpenGL : public IRenderer {
public:
    Status initialize(const RendererConfig& config) override {
        config_ = config;
        // TODO: Initialize OpenGL context
        return {};
    }
    
    void shutdown() override {
        // TODO: Cleanup OpenGL resources
    }
    
    RendererBackend backend() const noexcept override { 
        return RendererBackend::OpenGL; 
    }
    
    Status resize(uint32_t width, uint32_t height) override {
        config_.surface.width = width;
        config_.surface.height = height;
        // TODO: glViewport
        return {};
    }
    
    Status begin_frame() override {
        // TODO: Begin frame
        return {};
    }
    
    Status end_frame() override {
        // TODO: Swap buffers
        return {};
    }
    
    void clear(const ClearColor& color) override {
        // TODO: glClearColor, glClear
        (void)color;
    }
    
    void set_camera(const Camera& camera) override {
        camera_ = camera;
    }
    
    Status render_model(const Model& model, const Mat4& transform) override {
        // TODO: Draw model
        (void)model;
        (void)transform;
        return {};
    }
    
    void wait_idle() override {
        // TODO: glFinish
    }
    
private:
    RendererConfig config_;
    Camera camera_;
};
#endif

// ============================================================================
// Vulkan Renderer
// ============================================================================

#if defined(ETU_HAS_VULKAN)
class RendererVulkan : public IRenderer {
public:
    Status initialize(const RendererConfig& config) override {
        config_ = config;
        // TODO: Initialize Vulkan instance, device, swapchain
        return {};
    }
    
    void shutdown() override {
        // TODO: Cleanup Vulkan resources
    }
    
    RendererBackend backend() const noexcept override { 
        return RendererBackend::Vulkan; 
    }
    
    Status resize(uint32_t width, uint32_t height) override {
        config_.surface.width = width;
        config_.surface.height = height;
        // TODO: Recreate swapchain
        return {};
    }
    
    Status begin_frame() override {
        // TODO: Acquire next image, begin command buffer
        return {};
    }
    
    Status end_frame() override {
        // TODO: Submit command buffer, present
        return {};
    }
    
    void clear(const ClearColor& color) override {
        clear_color_ = color;
    }
    
    void set_camera(const Camera& camera) override {
        camera_ = camera;
    }
    
    Status render_model(const Model& model, const Mat4& transform) override {
        // TODO: Record draw commands
        (void)model;
        (void)transform;
        return {};
    }
    
    void wait_idle() override {
        // TODO: vkDeviceWaitIdle
    }
    
private:
    RendererConfig config_;
    Camera camera_;
    ClearColor clear_color_;
};
#endif

// ============================================================================
// DirectX 12 Renderer (Windows)
// ============================================================================

#if defined(ETU_HAS_DIRECTX) && defined(_WIN32)
class RendererDX12 : public IRenderer {
public:
    Status initialize(const RendererConfig& config) override {
        config_ = config;
        // TODO: Initialize D3D12 device, command queue, swapchain
        return {};
    }
    
    void shutdown() override {
        // TODO: Cleanup D3D12 resources
    }
    
    RendererBackend backend() const noexcept override { 
        return RendererBackend::DirectX12; 
    }
    
    Status resize(uint32_t width, uint32_t height) override {
        config_.surface.width = width;
        config_.surface.height = height;
        // TODO: Resize swapchain buffers
        return {};
    }
    
    Status begin_frame() override {
        // TODO: Wait for fence, reset command allocator
        return {};
    }
    
    Status end_frame() override {
        // TODO: Execute command list, present
        return {};
    }
    
    void clear(const ClearColor& color) override {
        clear_color_ = color;
    }
    
    void set_camera(const Camera& camera) override {
        camera_ = camera;
    }
    
    Status render_model(const Model& model, const Mat4& transform) override {
        // TODO: Record draw calls
        (void)model;
        (void)transform;
        return {};
    }
    
    void wait_idle() override {
        // TODO: Flush command queue
    }
    
private:
    RendererConfig config_;
    Camera camera_;
    ClearColor clear_color_;
};
#endif

// ============================================================================
// Metal Renderer (macOS/iOS)
// ============================================================================

#if defined(ETU_HAS_METAL) && defined(__APPLE__)
class RendererMetal : public IRenderer {
public:
    Status initialize(const RendererConfig& config) override {
        config_ = config;
        // TODO: Initialize Metal device, command queue, layer
        return {};
    }
    
    void shutdown() override {
        // TODO: Cleanup Metal resources
    }
    
    RendererBackend backend() const noexcept override { 
        return RendererBackend::Metal; 
    }
    
    Status resize(uint32_t width, uint32_t height) override {
        config_.surface.width = width;
        config_.surface.height = height;
        // TODO: Update drawable size
        return {};
    }
    
    Status begin_frame() override {
        // TODO: Get next drawable, create command buffer
        return {};
    }
    
    Status end_frame() override {
        // TODO: Present drawable, commit
        return {};
    }
    
    void clear(const ClearColor& color) override {
        clear_color_ = color;
    }
    
    void set_camera(const Camera& camera) override {
        camera_ = camera;
    }
    
    Status render_model(const Model& model, const Mat4& transform) override {
        // TODO: Encode draw calls
        (void)model;
        (void)transform;
        return {};
    }
    
    void wait_idle() override {
        // TODO: Wait for command buffer completion
    }
    
private:
    RendererConfig config_;
    Camera camera_;
    ClearColor clear_color_;
};
#endif

// ============================================================================
// Factory Functions
// ============================================================================

Result<Unique<IRenderer>> create_renderer(RendererBackend backend) {
    if (backend == RendererBackend::None) {
        backend = get_recommended_backend();
    }
    
    switch (backend) {
#if defined(ETU_HAS_METAL) && defined(__APPLE__)
        case RendererBackend::Metal:
            return make_unique<RendererMetal>();
#endif
#if defined(ETU_HAS_DIRECTX) && defined(_WIN32)
        case RendererBackend::DirectX12:
            return make_unique<RendererDX12>();
#endif
#if defined(ETU_HAS_VULKAN)
        case RendererBackend::Vulkan:
            return make_unique<RendererVulkan>();
#endif
#if defined(ETU_HAS_OPENGL)
        case RendererBackend::OpenGL:
            return make_unique<RendererOpenGL>();
#endif
        default:
            // Fallback to null renderer
            return make_unique<RendererNull>();
    }
}

std::vector<RendererBackend> get_available_backends() {
    std::vector<RendererBackend> backends;
    
#if defined(ETU_HAS_METAL) && defined(__APPLE__)
    backends.push_back(RendererBackend::Metal);
#endif
#if defined(ETU_HAS_DIRECTX) && defined(_WIN32)
    backends.push_back(RendererBackend::DirectX12);
#endif
#if defined(ETU_HAS_VULKAN)
    backends.push_back(RendererBackend::Vulkan);
#endif
#if defined(ETU_HAS_OPENGL)
    backends.push_back(RendererBackend::OpenGL);
#endif
    
    return backends;
}

RendererBackend get_recommended_backend() {
#if defined(__APPLE__)
    return RendererBackend::Metal;
#elif defined(_WIN32)
    return RendererBackend::DirectX12;
#elif defined(ETU_HAS_VULKAN)
    return RendererBackend::Vulkan;
#elif defined(ETU_HAS_OPENGL)
    return RendererBackend::OpenGL;
#else
    return RendererBackend::None;
#endif
}

} // namespace etu
