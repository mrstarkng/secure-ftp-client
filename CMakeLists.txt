# Phiên bản tối thiểu của CMake
cmake_minimum_required(VERSION 3.15)

# Tên project và ngôn ngữ sử dụng
project(SecureFtpClient LANGUAGES CXX)

# --- Tìm các gói cần thiết ---
find_package(Python REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

# --- Định nghĩa các file mã nguồn C++ ---
set(CPP_SOURCES
    src/client/binder.cpp
    src/common/socket_utils.cpp
    src/connectors/clamav_connector.cpp
    src/core/command_handler.cpp
    src/core/ftp_connection.cpp
    src/core/ftp_directory_ops.cpp
    src/core/ftp_file_ops.cpp
)

# ====================================================================
# === THAY ĐỔI THỨ TỰ Ở ĐÂY ===
# ====================================================================

# --- BƯỚC 1: TẠO MODULE PYTHON (TARGET) TRƯỚC ---
# Lệnh này sẽ tạo ra một target tên là "ftp_engine"
pybind11_add_module(ftp_engine ${CPP_SOURCES})

# --- BƯỚC 2: CẤU HÌNH CHO TARGET VỪA TẠO ---
# Bây giờ CMake đã biết "ftp_engine" là gì, chúng ta có thể cấu hình nó.

# Thêm các thư mục include để trình biên dịch tìm thấy các file .h
target_include_directories(ftp_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/common
    ${CMAKE_CURRENT_SOURCE_DIR}/src/connectors
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core
)

# --- Cấu hình dành riêng cho Windows ---
if(WIN32)
    # Link với thư viện WinSock (ws2_32.lib)
    target_link_libraries(ftp_engine PRIVATE ws2_32)

    # ====================================================================
    # === TỰ ĐỘNG SAO CHÉP CÁC FILE CẦN THIẾT SAU KHI BUILD XONG ===
    # ====================================================================

    set(FRONTEND_DIR ${CMAKE_SOURCE_DIR}/frontend)

    # 1. Tự động sao chép file .pyd
    add_custom_command(
        TARGET ftp_engine POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_FILE:ftp_engine>
                ${FRONTEND_DIR}
        COMMENT "Copying ftp_engine module to frontend directory..."
    )

    # 2. Tự động sao chép các DLL của MinGW
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