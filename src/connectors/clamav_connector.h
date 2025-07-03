#pragma once
#include <string>

// Đổi tên 'ERROR' thành 'SCAN_ERROR' để tránh xung đột với macro của Windows
enum class ScanResult { OK, INFECTED, SCAN_ERROR };

class ClamavConnector {
public:
    ClamavConnector(const std::string& agent_host, int agent_port);
    ScanResult scanFile(const std::string& local_file_path);
private:
    std::string host;
    int port;
};