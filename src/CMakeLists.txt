cmake_minimum_required(VERSION 3.25)
project(ETU 
    VERSION 0.1.0
    DESCRIPTION "AI Pipelining for Dynamic 3D Model Creation"
    LANGUAGES CXX
)

# ============================================================================
# C++23 Standard (Required)
# ============================================================================
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile_commands.json for IDE/LSP support
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# Build Options
# ============================================================================
option(ETU_BUILD_TESTS "Build unit tests" ON)
option(ETU_BUILD_EXAMPLES "Build example applications" ON)
option(ETU_ENABLE_GPU "Enable GPU acceleration (CUDA/Metal/Vulkan Compute)" ON)

# Rendering backend options (auto-detect by default)
option(ETU_USE_VULKAN "Use Vulkan rendering backend" OFF)
option(ETU_USE_DIRECTX "Use DirectX 12 rendering backend (Windows only)" OFF)
option(ETU_USE_METAL "Use Metal rendering backend (macOS/iOS only)" OFF)
option(ETU_USE_OPENGL "Use OpenGL rendering backend (fallback)" OFF)
option(ETU_AUTO_DETECT_RENDERER "Auto-detect best rendering backend" ON)

# ============================================================================
# Platform Detection & Renderer Auto-Selection
# ============================================================================
if(ETU_AUTO_DETECT_RENDERER)
    if(WIN32)
        # Windows: Prefer DirectX 12, fallback to Vulkan, then OpenGL
        set(ETU_USE_DIRECTX ON CACHE BOOL "" FORCE)
        message(STATUS "[ETU] Platform: Windows - Using DirectX 12 (primary)")
    elseif(APPLE)
        # macOS/iOS: Use Metal
        set(ETU_USE_METAL ON CACHE BOOL "" FORCE)
        message(STATUS "[ETU] Platform: Apple - Using Metal (primary)")
    else()
        # Linux/Other: Prefer Vulkan, fallback to OpenGL
        set(ETU_USE_VULKAN ON CACHE BOOL "" FORCE)
        message(STATUS "[ETU] Platform: Linux - Using Vulkan (primary)")
    endif()
    # Always enable OpenGL as fallback
    set(ETU_USE_OPENGL ON CACHE BOOL "" FORCE)
endif()

# ============================================================================
# Compiler-Specific Settings
# ============================================================================
if(MSVC)
    # Visual Studio 2022+ settings
    add_compile_options(
        /W4                 # Warning level 4
        /permissive-        # Strict conformance mode
        /Zc:__cplusplus     # Correct __cplusplus macro
        /Zc:preprocessor    # Standard-conforming preprocessor
        /utf-8              # UTF-8 source and execution charset
        /EHsc               # Standard exception handling
        /MP                 # Multi-processor compilation
    )
    # Enable C++23 modules support (VS 2022 17.4+)
    if(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "19.34")
        add_compile_options(/experimental:module)
    endif()
    # Release optimizations
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /O2 /GL /DNDEBUG")
    set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS_RELEASE} /LTCG")
else()
    # Clang/GCC settings
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
        -fPIC
    )
    if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        add_compile_options(-stdlib=libc++)
        add_link_options(-stdlib=libc++)
    endif()
    # Release optimizations
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -DNDEBUG -march=native")
endif()

# ============================================================================
# Find Dependencies
# ============================================================================

# --- Rendering Backends ---
if(ETU_USE_VULKAN)
    find_package(Vulkan QUIET)
    if(Vulkan_FOUND)
        message(STATUS "[ETU] Vulkan found: ${Vulkan_LIBRARY}")
        list(APPEND ETU_RENDERER_LIBS Vulkan::Vulkan)
        add_compile_definitions(ETU_HAS_VULKAN=1)
    else()
        message(WARNING "[ETU] Vulkan requested but not found")
        set(ETU_USE_VULKAN OFF)
    endif()
endif()

if(ETU_USE_DIRECTX AND WIN32)
    # DirectX 12 is part of Windows SDK
    add_compile_definitions(ETU_HAS_DIRECTX=1)
    list(APPEND ETU_RENDERER_LIBS d3d12 dxgi d3dcompiler)
    message(STATUS "[ETU] DirectX 12 enabled")
endif()

if(ETU_USE_METAL AND APPLE)
    find_library(METAL_FRAMEWORK Metal)
    find_library(METALKIT_FRAMEWORK MetalKit)
    find_library(QUARTZCORE_FRAMEWORK QuartzCore)
    if(METAL_FRAMEWORK)
        add_compile_definitions(ETU_HAS_METAL=1)
        list(APPEND ETU_RENDERER_LIBS 
            ${METAL_FRAMEWORK} 
            ${METALKIT_FRAMEWORK} 
            ${QUARTZCORE_FRAMEWORK}
        )
        message(STATUS "[ETU] Metal enabled")
    endif()
endif()

if(ETU_USE_OPENGL)
    find_package(OpenGL QUIET)
    if(OpenGL_FOUND)
        add_compile_definitions(ETU_HAS_OPENGL=1)
        list(APPEND ETU_RENDERER_LIBS OpenGL::GL)
        message(STATUS "[ETU] OpenGL found (fallback renderer)")
    endif()
endif()

# --- GPU Acceleration ---
if(ETU_ENABLE_GPU)
    # CUDA (NVIDIA)
    include(CheckLanguage)
    check_language(CUDA)
    if(CMAKE_CUDA_COMPILER)
        enable_language(CUDA)
        set(CMAKE_CUDA_STANDARD 17)
        set(CMAKE_CUDA_STANDARD_REQUIRED ON)
        add_compile_definitions(ETU_HAS_CUDA=1)
        message(STATUS "[ETU] CUDA enabled: ${CMAKE_CUDA_COMPILER_VERSION}")
    endif()
    
    # Metal Performance Shaders (Apple)
    if(APPLE)
        find_library(MPS_FRAMEWORK MetalPerformanceShaders)
        if(MPS_FRAMEWORK)
            add_compile_definitions(ETU_HAS_MPS=1)
            list(APPEND ETU_GPU_LIBS ${MPS_FRAMEWORK})
            message(STATUS "[ETU] Metal Performance Shaders enabled")
        endif()
    endif()
endif()

# ============================================================================
# ETU Library
# ============================================================================
add_library(etu_core STATIC
    src/etu.cpp
    src/pipeline.cpp
    src/renderer.cpp
    src/gpu_context.cpp
)

target_include_directories(etu_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(etu_core
    PUBLIC
        ${ETU_RENDERER_LIBS}
        ${ETU_GPU_LIBS}
)

# ============================================================================
# Main Executable
# ============================================================================
add_executable(etu_app src/main.cpp)
target_link_libraries(etu_app PRIVATE etu_core)

# ============================================================================
# Tests
# ============================================================================
if(ETU_BUILD_TESTS)
    enable_testing()
    
    # Simple test without external framework
    add_executable(etu_tests tests/test_main.cpp)
    target_link_libraries(etu_tests PRIVATE etu_core)
    add_test(NAME etu_tests COMMAND etu_tests)
endif()

# ============================================================================
# Installation
# ============================================================================
install(TARGETS etu_core etu_app
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/etu DESTINATION include)

# ============================================================================
# Summary
# ============================================================================
message(STATUS "")
message(STATUS "========== ETU Build Configuration ==========")
message(STATUS "  C++ Standard:    C++${CMAKE_CXX_STANDARD}")
message(STATUS "  Build Type:      ${CMAKE_BUILD_TYPE}")
message(STATUS "  Compiler:        ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  Renderers:       ${ETU_RENDERER_LIBS}")
message(STATUS "  GPU Accel:       ${ETU_ENABLE_GPU}")
message(STATUS "  Tests:           ${ETU_BUILD_TESTS}")
message(STATUS "==============================================")
message(STATUS "")
