#pragma once
/**
 * @file pipeline.hpp
 * @brief AI Pipeline for Dynamic 3D Model Creation
 */

#include "etu/types.hpp"
#include <functional>
#include <future>

namespace etu {

// ============================================================================
// Pipeline Stage Types
// ============================================================================

/**
 * @brief Pipeline processing stages
 */
enum class PipelineStage : uint8_t {
    Input,          // Data input/loading
    Preprocess,     // Data preprocessing
    Inference,      // AI model inference
    PostProcess,    // Post-processing
    Rendering,      // 3D rendering
    Output          // Final output
};

/**
 * @brief Stage execution status
 */
struct StageResult {
    PipelineStage stage;
    bool success;
    double execution_time_ms;
    std::string message;
};

// ============================================================================
// Pipeline Configuration
// ============================================================================

/**
 * @brief Configuration for the AI pipeline
 */
struct PipelineConfig {
    bool use_gpu = true;
    uint32_t batch_size = 1;
    uint32_t max_vertices = 1'000'000;
    uint32_t max_triangles = 500'000;
    float quality_level = 1.0f;         // 0.0 - 1.0
    bool enable_caching = true;
    std::string cache_directory;
};

// ============================================================================
// Pipeline Interface
// ============================================================================

/**
 * @brief Main AI Pipeline class for dynamic 3D model creation
 * 
 * This pipeline processes input data through multiple stages:
 * 1. Input loading and validation
 * 2. Preprocessing and feature extraction
 * 3. AI model inference
 * 4. Post-processing and mesh generation
 * 5. Rendering preparation
 * 6. Final output
 */
class Pipeline {
public:
    /**
     * @brief Progress callback type
     * @param stage Current stage
     * @param progress Progress within stage (0.0 - 1.0)
     * @param message Status message
     */
    using ProgressCallback = std::function<void(PipelineStage stage, float progress, std::string_view message)>;

    Pipeline();
    ~Pipeline();
    
    // Non-copyable, movable
    Pipeline(const Pipeline&) = delete;
    Pipeline& operator=(const Pipeline&) = delete;
    Pipeline(Pipeline&&) noexcept;
    Pipeline& operator=(Pipeline&&) noexcept;

    /**
     * @brief Configure the pipeline
     */
    Status configure(const PipelineConfig& config);

    /**
     * @brief Get current configuration
     */
    [[nodiscard]] const PipelineConfig& config() const noexcept;

    /**
     * @brief Set progress callback
     */
    void set_progress_callback(ProgressCallback callback);

    /**
     * @brief Process input data and generate 3D model (synchronous)
     * @param input_data Raw input data (image, point cloud, etc.)
     * @return Generated 3D model or error
     */
    [[nodiscard]] Result<Model> process(std::span<const std::byte> input_data);

    /**
     * @brief Process input data asynchronously
     * @param input_data Raw input data
     * @return Future containing the result
     */
    [[nodiscard]] std::future<Result<Model>> process_async(std::span<const std::byte> input_data);

    /**
     * @brief Cancel ongoing processing
     */
    void cancel();

    /**
     * @brief Check if pipeline is currently processing
     */
    [[nodiscard]] bool is_processing() const noexcept;

    /**
     * @brief Get the last execution results for each stage
     */
    [[nodiscard]] std::vector<StageResult> get_stage_results() const;

private:
    struct Impl;
    Unique<Impl> pimpl_;
};

// ============================================================================
// Pipeline Builder (Fluent API)
// ============================================================================

/**
 * @brief Builder for creating configured pipelines
 */
class PipelineBuilder {
public:
    PipelineBuilder() = default;
    
    PipelineBuilder& with_gpu(bool enable = true);
    PipelineBuilder& with_batch_size(uint32_t size);
    PipelineBuilder& with_quality(float level);
    PipelineBuilder& with_caching(bool enable, std::string_view cache_dir = "");
    PipelineBuilder& with_limits(uint32_t max_vertices, uint32_t max_triangles);
    
    [[nodiscard]] Result<Pipeline> build();

private:
    PipelineConfig config_;
};

} // namespace etu
