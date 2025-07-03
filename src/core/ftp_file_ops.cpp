#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include <fstream>
#include <iostream>

bool FtpController::deleteFile(const std::string& remote_path) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand("DELE " + remote_path);
    // ... kiểm tra response code ...
    return true;
}

bool FtpController::renameFile(const std::string& from, const std::string& to) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand("RNFR " + from);
    readReply(); // Chờ 350
    sendCommand("RNTO " + to);
    // ... kiểm tra response code ...
    return true;
}

bool FtpController::downloadFile(const std::string& remote, const std::string& local) {
    if (!isConnected()) throw FtpException("Not connected.");
    // ... logic download tương tự upload ...
    return true;
}

bool FtpController::uploadFile(const std::string& local, const std::string& remote) {
    if (!isConnected()) throw FtpException("Not connected.");
    std::ifstream file(local, std::ios::binary);
    if (!file.is_open()) throw FtpException("Cannot open local file: " + local);

    // SOCKET data_socket = createDataConnection();
    // sendCommand("STOR " + remote);
    // ... logic gửi file qua data_socket ...
    return true;
}