#pragma once
#include "ftp_controller.h"
#include "../connectors/clamav_connector.h"
#include "../common/socket_utils.h"
#include <vector>
#include <string>
#include <filesystem> // Add for local file system operations

class CommandHandler {
public:
    CommandHandler();

    // --- 3. Session Management ---
    std::string handle_open(const std::vector<std::string>& args);
    std::string handle_close();
    std::string handle_quit();
    std::string handle_status();
    std::string handle_passive(const std::vector<std::string>& args); // Đổi lại để nhận vector
    std::string handle_binary();
    std::string handle_ascii();
    std::string handle_prompt();
    std::string handle_help(); // Thêm hàm help

    // --- 1. File and Directory Operations ---
    std::string handle_ls(const std::vector<std::string>& args);
    std::string handle_cd(const std::vector<std::string>& args);
    std::string handle_pwd();
    std::string handle_mkdir(const std::vector<std::string>& args);
    std::string handle_rmdir(const std::vector<std::string>& args);
    std::string handle_delete(const std::vector<std::string>& args);
    std::string handle_rename(const std::vector<std::string>& args);

    // --- 2. Upload and Download ---
    std::string handle_get(const std::vector<std::string>& args);
    std::string handle_put(const std::vector<std::string>& args);
    std::string handle_mget(const std::vector<std::string>& args);
    std::string handle_mput(const std::vector<std::string>& args);

private:
    // Add private helpers for recursion
    void mgetRecursive(const std::string& remote_path, const std::string& local_path);
    void mputRecursive(const std::filesystem::path& local_path, const std::string& remote_path);

    FtpController ftp;
    ClamavConnector av;
    WsaInitializer wsa;
    bool prompt_mode = true;
};