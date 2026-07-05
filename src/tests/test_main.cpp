/**
 * @file test_main.cpp
 * @brief Unit tests for ETU library
 */

#include "etu/etu.hpp"
#include <iostream>
#include <cassert>

#define TEST(name) void test_##name()
#define RUN_TEST(name) do { \
    std::cout << "Running " #name "... "; \
    test_##name(); \
    std::cout << "PASSED" << std::endl; \
} while(0)

// ============================================================================
// Type Tests
// ============================================================================

TEST(vec3_construction) {
    etu::Vec3 v1;
    assert(v1.x == 0 && v1.y == 0 && v1.z == 0);
    
    etu::Vec3 v2{1.0f, 2.0f, 3.0f};
    assert(v2.x == 1.0f && v2.y == 2.0f && v2.z == 3.0f);
}

TEST(mat4_identity) {
    etu::Mat4 m = etu::Mat4::identity();
    assert(m.data[0] == 1.0f);
    assert(m.data[5] == 1.0f);
    assert(m.data[10] == 1.0f);
    assert(m.data[15] == 1.0f);
}

TEST(error_code) {
    etu::Error err{etu::ErrorCode::Success, "OK", ""};
    assert(err.is_success());
    assert(!err);
    
    etu::Error err2{etu::ErrorCode::InvalidArgument, "Bad", ""};
    assert(!err2.is_success());
    assert(err2);
}

TEST(renderer_backend_string) {
    assert(etu::to_string(etu::RendererBackend::OpenGL) == "OpenGL");
    assert(etu::to_string(etu::RendererBackend::Vulkan) == "Vulkan");
    assert(etu::to_string(etu::RendererBackend::DirectX12) == "DirectX 12");
    assert(etu::to_string(etu::RendererBackend::Metal) == "Metal");
    assert(etu::to_string(etu::RendererBackend::None) == "None");
}

// ============================================================================
// Library Tests
// ============================================================================

TEST(initialize_shutdown) {
    assert(!etu::is_initialized());
    
    bool result = etu::initialize();
    assert(result);
    assert(etu::is_initialized());
    
    etu::shutdown();
    assert(!etu::is_initialized());
}

TEST(double_initialize) {
    assert(etu::initialize());
    assert(etu::initialize()); // Should succeed (already initialized)
    assert(etu::is_initialized());
    
    etu::shutdown();
}

TEST(get_available_backends) {
    etu::initialize();
    
    auto backends = etu::get_available_backends();
    // Should have at least one backend on any system
    // (or none if compiled without graphics support)
    
    auto recommended = etu::get_recommended_backend();
    // Verify recommended is either in the list or None
    bool found = (recommended == etu::RendererBackend::None);
    for (auto b : backends) {
        if (b == recommended) found = true;
    }
    assert(found);
    
    etu::shutdown();
}

// ============================================================================
// Pipeline Tests
// ============================================================================

TEST(pipeline_builder) {
    etu::initialize();
    
    auto result = etu::PipelineBuilder()
        .with_gpu(false)
        .with_quality(0.5f)
        .with_batch_size(4)
        .build();
    
    assert(result.has_value());
    
    const auto& config = result->config();
    assert(!config.use_gpu);
    assert(config.quality_level == 0.5f);
    assert(config.batch_size == 4);
    
    etu::shutdown();
}

TEST(pipeline_process_empty) {
    etu::initialize();
    
    auto pipeline_result = etu::PipelineBuilder().build();
    assert(pipeline_result.has_value());
    
    std::span<const std::byte> empty_data;
    auto result = pipeline_result->process(empty_data);
    
    // Should fail with empty input
    assert(!result.has_value());
    assert(result.error().code == etu::ErrorCode::InvalidArgument);
    
    etu::shutdown();
}

TEST(pipeline_process_valid) {
    etu::initialize();
    
    auto pipeline_result = etu::PipelineBuilder()
        .with_gpu(false)
        .build();
    assert(pipeline_result.has_value());
    
    std::vector<std::byte> dummy_data(100);
    auto result = pipeline_result->process(dummy_data);
    
    assert(result.has_value());
    assert(!result->name.empty());
    assert(!result->meshes.empty());
    
    etu::shutdown();
}

TEST(pipeline_progress_callback) {
    etu::initialize();
    
    auto pipeline_result = etu::PipelineBuilder()
        .with_gpu(false)
        .build();
    assert(pipeline_result.has_value());
    
    int callback_count = 0;
    pipeline_result->set_progress_callback([&callback_count](etu::PipelineStage, float, std::string_view) {
        callback_count++;
    });
    
    std::vector<std::byte> dummy_data(100);
    auto result = pipeline_result->process(dummy_data);
    
    assert(result.has_value());
    assert(callback_count > 0); // Should have been called multiple times
    
    etu::shutdown();
}

// ============================================================================
// GPU Context Tests
// ============================================================================

TEST(gpu_context_creation) {
    etu::GPUContext ctx;
    assert(!ctx.is_available());
    
    auto status = ctx.initialize();
    // May or may not succeed depending on hardware
    
    if (ctx.is_available()) {
        auto caps = ctx.capabilities();
        assert(!caps.device_name.empty());
    }
    
    ctx.shutdown();
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "ETU Unit Tests\n";
    std::cout << "==============\n\n";
    
    // Type tests
    RUN_TEST(vec3_construction);
    RUN_TEST(mat4_identity);
    RUN_TEST(error_code);
    RUN_TEST(renderer_backend_string);
    
    // Library tests
    RUN_TEST(initialize_shutdown);
    RUN_TEST(double_initialize);
    RUN_TEST(get_available_backends);
    
    // Pipeline tests
    RUN_TEST(pipeline_builder);
    RUN_TEST(pipeline_process_empty);
    RUN_TEST(pipeline_process_valid);
    RUN_TEST(pipeline_progress_callback);
    
    // GPU tests
    RUN_TEST(gpu_context_creation);
    
    std::cout << "\n==============\n";
    std::cout << "All tests passed!\n";
    
    return 0;
}
