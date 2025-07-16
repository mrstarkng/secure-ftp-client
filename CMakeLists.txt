# Minimum required version of CMake
cmake_minimum_required(VERSION 3.15)

# Project name and language used
project(SecureFtpClient LANGUAGES CXX)

# Set default build type if not specified
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)
endif()

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Find required packages ---
find_package(Python REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

# --- Define C++ source files ---
set(CPP_SOURCES
    src/client/binder.cpp
    src/common/socket_utils.cpp
    src/connectors/clamav_connector.cpp
    src/core/command_handler.cpp
    src/core/ftp_connection.cpp
    src/core/ftp_directory_ops.cpp
    src/core/ftp_file_ops.cpp
)

# --- CREATE PYTHON MODULE (TARGET) ---
pybind11_add_module(ftp_engine ${CPP_SOURCES})

# --- CONFIGURE THE TARGET ---

# Add include directories
target_include_directories(ftp_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/common
    ${CMAKE_CURRENT_SOURCE_DIR}/src/connectors
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core
)

# ====================================================================
# === PERFORMANCE OPTIMIZATIONS ===
# ====================================================================

# 1. Enable Link-Time Optimization (LTO) for Release builds
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported)
if(ipo_supported)
    # Enable LTO (Interprocedural Optimization) only for Release configuration
    set_target_properties(ftp_engine PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE
    )
    message(STATUS "LTO (Link-Time Optimization) enabled for Release builds.")
endif()

# 2. Set Compiler Flags (Using -O3 for Release)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(ftp_engine PRIVATE 
        -Wall -Wextra -Wpedantic
        $<$<CONFIG:Debug>:-g -O0>
        # Changed -O2 to -O3 for maximum optimization in Release
        $<$<CONFIG:Release>:-O3 -DNDEBUG> 
        $<$<CONFIG:RelWithDebInfo>:-O2 -g>
    )
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    target_compile_options(ftp_engine PRIVATE 
        /W4
        $<$<CONFIG:Debug>:/Od /Zi>
        # /O2 is generally the max optimization for speed in MSVC
        $<$<CONFIG:Release>:/O2 /DNDEBUG> 
        $<$<CONFIG:RelWithDebInfo>:/O2 /Zi>
    )
endif()

# ====================================================================
# === Windows-specific configuration (Deployment) ===
# ====================================================================
if(WIN32)
    # Link with WinSock library (ws2_32.lib)
    target_link_libraries(ftp_engine PRIVATE ws2_32)

    set(FRONTEND_DIR ${CMAKE_SOURCE_DIR}/frontend)

    # 1. Automatically copy .pyd file
    add_custom_command(
        TARGET ftp_engine POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_FILE:ftp_engine>
                ${FRONTEND_DIR}
        COMMENT "Copying ftp_engine module to frontend directory..."
    )

    # 2. Automatically copy MinGW DLLs
    # (This part remains the same as it's for deployment, not performance)
    get_filename_component(MINGW_BIN_DIR ${CMAKE_CXX_COMPILER} DIRECTORY)
    set(REQUIRED_DLLS
        "libgcc_s_seh-1.dll"
        "libstdc++-6.dll"
        "libwinpthread-1.dll"
    )
    foreach(DLL_NAME ${REQUIRED_DLLS})
        set(DLL_PATH "${MINGW_BIN_DIR}/${DLL_NAME}")
        if(EXISTS ${DLL_PATH})
            add_custom_command(
                TARGET ftp_engine POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                        ${DLL_PATH}
                        ${FRONTEND_DIR}
                COMMENT "Copying dependency ${DLL_NAME} to frontend directory..."
            )
        endif()
    endforeach()
endif()