#pragma once

#include <stdexcept>
#include <string>

// Custom exception để xử lý lỗi một cách nhất quán
class FtpException : public std::runtime_error {
public:
    explicit FtpException(const std::string& message) : std::runtime_error(message) {}
};

// Lớp RAII để tự động khởi tạo và dọn dẹp WinSock
class WsaInitializer {
public:
    WsaInitializer();
    ~WsaInitializer();
};