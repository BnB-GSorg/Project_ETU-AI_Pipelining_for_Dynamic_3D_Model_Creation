/**
 * @file etu.cpp
 * @brief Core ETU library implementation
 */

#include "etu/etu.hpp"
#include <atomic>
#include <mutex>

namespace etu {

namespace {
    std::atomic<bool> g_initialized{false};
    std::mutex g_init_mutex;
    Config g_config;
    Unique<GPUContext> g_gpu_context;
    RendererBackend g_active_renderer = RendererBackend::None;
}

bool initialize(const Config& config) {
    std::lock_guard<std::mutex> lock(g_init_mutex);
    
    if (g_initialized.load()) {
        return true; // Already initialized
    }
    
    g_config = config;
    
    // Initialize GPU context if enabled
    if (config.enable_gpu_acceleration) {
        g_gpu_context = make_unique<GPUContext>();
        if (auto status = g_gpu_context->initialize(); !status) {
            // GPU init failed, continue without it
            g_gpu_context.reset();
        }
    }
    
    // Determine active renderer
    g_active_renderer = get_recommended_backend();
    if (config.preferred_renderer != RendererBackend::None) {
        auto available = get_available_backends();
        for (auto backend : available) {
            if (backend == config.preferred_renderer) {
                g_active_renderer = config.preferred_renderer;
                break;
            }
        }
    }
    
    g_initialized.store(true);
    return true;
}

void shutdown() {
    std::lock_guard<std::mutex> lock(g_init_mutex);
    
    if (!g_initialized.load()) {
        return;
    }
    
    if (g_gpu_context) {
        g_gpu_context->shutdown();
        g_gpu_context.reset();
    }
    
    g_active_renderer = RendererBackend::None;
    g_initialized.store(false);
}

bool is_initialized() noexcept {
    return g_initialized.load();
}

RendererBackend get_active_renderer() noexcept {
    return g_active_renderer;
}

GPUCapabilities get_gpu_capabilities() noexcept {
    if (g_gpu_context && g_gpu_context->is_available()) {
        return g_gpu_context->capabilities();
    }
    return GPUCapabilities{};
}

} // namespace etu
