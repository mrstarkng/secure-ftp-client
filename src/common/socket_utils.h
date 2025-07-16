#pragma once

#include <stdexcept>
#include <string>
#include <vector> // Thêm include này

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

// --- THÊM CÁC KHAI BÁO HÀM HELPER VÀO ĐÂY ---
int parseResponseCode(const std::string& response);
bool isSuccessCode(int code);