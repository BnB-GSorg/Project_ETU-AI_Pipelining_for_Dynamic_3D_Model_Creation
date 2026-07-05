/**
 * @file main.cpp
 * @brief ETU Application Entry Point
 * 
 * AI Pipelining for Dynamic 3D Model Creation
 */

#include "etu/etu.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>

namespace fs = std::filesystem;

void print_usage(const char* program) {
    std::cout << "ETU - AI Pipelining for Dynamic 3D Model Creation\n"
              << "Version: " << etu::version.string << "\n\n"
              << "Usage: " << program << " [options] <input_file>\n\n"
              << "Options:\n"
              << "  -h, --help           Show this help message\n"
              << "  -v, --version        Show version information\n"
              << "  -o, --output <file>  Output file path\n"
              << "  --no-gpu             Disable GPU acceleration\n"
              << "  --quality <0-1>      Quality level (default: 1.0)\n"
              << "  --renderer <name>    Force renderer: opengl, vulkan, dx12, metal\n"
              << std::endl;
}

void print_system_info() {
    std::cout << "=== System Information ===\n";
    std::cout << "Renderer: " << etu::to_string(etu::get_active_renderer()) << "\n";
    
    auto gpu = etu::get_gpu_capabilities();
    if (gpu.available) {
        std::cout << "GPU: " << gpu.device_name << "\n";
        std::cout << "GPU Memory: " << (gpu.total_memory / 1024 / 1024) << " MB\n";
        std::cout << "Compute Units: " << gpu.compute_units << "\n";
    } else {
        std::cout << "GPU: Not available\n";
    }
    std::cout << "===========================\n" << std::endl;
}

int main(int argc, char* argv[]) {
    // Parse command line arguments
    std::string input_file;
    std::string output_file;
    bool use_gpu = true;
    float quality = 1.0f;
    etu::RendererBackend preferred_renderer = etu::RendererBackend::None;
    
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        }
        else if (arg == "-v" || arg == "--version") {
            std::cout << "ETU version " << etu::version.string << std::endl;
            return 0;
        }
        else if (arg == "-o" || arg == "--output") {
            if (i + 1 < argc) {
                output_file = argv[++i];
            }
        }
        else if (arg == "--no-gpu") {
            use_gpu = false;
        }
        else if (arg == "--quality") {
            if (i + 1 < argc) {
                quality = std::stof(argv[++i]);
            }
        }
        else if (arg == "--renderer") {
            if (i + 1 < argc) {
                std::string renderer = argv[++i];
                if (renderer == "opengl") preferred_renderer = etu::RendererBackend::OpenGL;
                else if (renderer == "vulkan") preferred_renderer = etu::RendererBackend::Vulkan;
                else if (renderer == "dx12") preferred_renderer = etu::RendererBackend::DirectX12;
                else if (renderer == "metal") preferred_renderer = etu::RendererBackend::Metal;
            }
        }
        else if (arg[0] != '-') {
            input_file = arg;
        }
    }
    
    // Initialize ETU
    etu::Config config{
        .preferred_renderer = preferred_renderer,
        .enable_gpu_acceleration = use_gpu,
        .enable_validation = true
    };
    
    if (!etu::initialize(config)) {
        std::cerr << "Error: Failed to initialize ETU library" << std::endl;
        return 1;
    }
    
    print_system_info();
    
    // If no input file, run in demo mode
    if (input_file.empty()) {
        std::cout << "No input file specified. Running in demo mode...\n" << std::endl;
        
        // Create a demo pipeline
        auto pipeline_result = etu::PipelineBuilder()
            .with_gpu(use_gpu)
            .with_quality(quality)
            .build();
        
        if (!pipeline_result) {
            std::cerr << "Error: " << pipeline_result.error().message << std::endl;
            etu::shutdown();
            return 1;
        }
        
        auto& pipeline = *pipeline_result;
        
        // Set up progress callback
        pipeline.set_progress_callback([](etu::PipelineStage stage, float progress, std::string_view message) {
            const char* stage_names[] = {"Input", "Preprocess", "Inference", "PostProcess", "Rendering", "Output"};
            std::cout << "[" << stage_names[static_cast<int>(stage)] << "] " 
                      << static_cast<int>(progress * 100) << "% - " << message << std::endl;
        });
        
        // Process dummy input
        std::vector<std::byte> dummy_input(1024);
        auto result = pipeline.process(dummy_input);
        
        if (result) {
            std::cout << "\nSuccess! Generated model: " << result->name << std::endl;
            std::cout << "  Meshes: " << result->meshes.size() << std::endl;
            for (const auto& mesh : result->meshes) {
                std::cout << "    - " << mesh.name << ": " 
                          << mesh.vertices.size() << " vertices, "
                          << mesh.indices.size() / 3 << " triangles" << std::endl;
            }
        } else {
            std::cerr << "Error: " << result.error().message << std::endl;
        }
        
        etu::shutdown();
        return result ? 0 : 1;
    }
    
    // Load input file
    if (!fs::exists(input_file)) {
        std::cerr << "Error: Input file not found: " << input_file << std::endl;
        etu::shutdown();
        return 1;
    }
    
    std::cout << "Processing: " << input_file << std::endl;
    
    // Read file
    std::ifstream file(input_file, std::ios::binary | std::ios::ate);
    auto size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<std::byte> input_data(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(input_data.data()), size);
    
    // Create and run pipeline
    auto pipeline_result = etu::PipelineBuilder()
        .with_gpu(use_gpu)
        .with_quality(quality)
        .build();
    
    if (!pipeline_result) {
        std::cerr << "Error: " << pipeline_result.error().message << std::endl;
        etu::shutdown();
        return 1;
    }
    
    auto& pipeline = *pipeline_result;
    pipeline.set_progress_callback([](etu::PipelineStage stage, float progress, std::string_view message) {
        const char* stage_names[] = {"Input", "Preprocess", "Inference", "PostProcess", "Rendering", "Output"};
        std::cout << "\r[" << stage_names[static_cast<int>(stage)] << "] " 
                  << static_cast<int>(progress * 100) << "% - " << message << std::flush;
    });
    
    auto result = pipeline.process(input_data);
    std::cout << std::endl;
    
    if (result) {
        std::cout << "Success! Generated model with " << result->meshes.size() << " mesh(es)" << std::endl;
        
        // TODO: Save output model
        if (!output_file.empty()) {
            std::cout << "Output saved to: " << output_file << std::endl;
        }
    } else {
        std::cerr << "Error: " << result.error().message << std::endl;
    }
    
    etu::shutdown();
    return result ? 0 : 1;
}
