#pragma once
#include <string>
#include <vector>
#include <functional>
#include <winsock2.h>

// Enum để định nghĩa chế độ truyền file
enum class TransferMode { ASCII, BINARY };

class FtpController {
public:
    FtpController();
    ~FtpController();

    // --- Connection Management ---
    bool connect(const std::string& host, int port);
    bool login(const std::string& user, const std::string& pass);
    void disconnect();
    bool isConnected() const;

    // --- Session Configuration ---
    void setTransferMode(TransferMode mode);
    void setPassive(bool is_passive);
    std::string getStatus();
    bool isPassive() const { return is_passive_mode; }

    // --- Directory Operations ---
    std::string listDirectory(const std::string& path);
    std::string printWorkingDirectory();
    bool changeDirectory(const std::string& path);
    bool makeDirectory(const std::string& path);
    bool removeDirectory(const std::string& path);

    // --- File Operations ---
    bool deleteFile(const std::string& remote_path);
    bool renameFile(const std::string& from, const std::string& to);
    bool downloadFile(const std::string& remote, const std::string& local);
    bool uploadFile(const std::string& local, const std::string& remote);

private:
    SOCKET control_socket = INVALID_SOCKET;
    bool is_passive_mode = true;
    TransferMode current_mode = TransferMode::BINARY;
    std::string current_host;
    std::string current_user;

    // Bộ đệm cho các phản hồi từ control connection để xử lý lỗi đồng bộ hóa
    std::string control_buffer; 

    // Các hàm helper private
    void sendCommand(const std::string& cmd);
    std::string readReply();
    SOCKET createDataConnection();
};