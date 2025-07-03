cmake_minimum_required(VERSION 3.18)
project(ftp_engine)

# --- Tìm các gói cần thiết ---
find_package(Python REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)
find_package(Threads REQUIRED)

# --- Định nghĩa các file mã nguồn một cách tường minh ---
# Đây là cách làm đáng tin cậy hơn là dùng GLOB_RECURSE
set(SRC_FILES
    src/client/binder.cpp
    src/common/socket_utils.cpp
    src/connectors/clamav_connector.cpp
    src/core/command_handler.cpp
    src/core/ftp_connection.cpp
    src/core/ftp_directory_ops.cpp
    src/core/ftp_file_ops.cpp
)

# --- Tạo module Python ---
pybind11_add_module(ftp_engine ${SRC_FILES})

# --- Liên kết các thư viện cần thiết ---
target_link_libraries(ftp_engine PRIVATE
    pybind11::module
    Threads::Threads
    Python::Python
    ws2_32
)

set_target_properties(ftp_engine PROPERTIES SUFFIX ".pyd")