#pragma once
#include <string>
#include <vector>
#include <functional>
#include <utility>
#include <winsock2.h>

// Enum để định nghĩa chế độ truyền file
enum class TransferMode { ASCII, BINARY };

// Progress callback type: (bytes_transferred, total_bytes) -> void
using ProgressCallback = std::function<void(size_t, size_t)>;

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
    std::vector<std::pair<std::string, bool>> parseListOutput(const std::string& list_data);
    bool changeDirectory(const std::string& path);
    bool makeDirectory(const std::string& path);
    bool removeDirectory(const std::string& path);

    // --- File Operations ---
    bool deleteFile(const std::string& remote_path);
    bool renameFile(const std::string& from, const std::string& to);
    bool downloadFile(const std::string& remote, const std::string& local);
    bool uploadFile(const std::string& local, const std::string& remote);
    
    // --- File Operations with Progress Callbacks ---
    bool downloadFileWithProgress(const std::string& remote, const std::string& local, ProgressCallback callback = nullptr);
    bool uploadFileWithProgress(const std::string& local, const std::string& remote, ProgressCallback callback = nullptr);

private:
    SOCKET control_socket = INVALID_SOCKET;
    bool is_passive_mode = true;
    TransferMode current_mode = TransferMode::BINARY;
    std::string current_host;
    std::string current_user;

    std::string control_buffer; 

    void sendCommand(const std::string& cmd);
    std::string readReply();
    SOCKET createDataConnection();
};