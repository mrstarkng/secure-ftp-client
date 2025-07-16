#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <ws2tcpip.h>
#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>

// =================================================================
// Constructor & Destructor
// =================================================================

FtpController::FtpController() {}

FtpController::~FtpController() {
    if (isConnected()) {
        disconnect();
    }
}

// =================================================================
// Private Helper Functions
// =================================================================

void FtpController::sendCommand(const std::string& cmd) {
    if (!isConnected()) {
        throw FtpException("Cannot send command: Not connected.");
    }
    std::cout << "CLIENT > " << cmd << std::endl;
    std::string full_cmd = cmd + "\r\n";
    if (send(control_socket, full_cmd.c_str(), (int)full_cmd.length(), 0) == SOCKET_ERROR) {
        throw FtpException("Failed to send command to server.");
    }
}

// Hàm readReply thông minh với bộ đệm - ĐÂY LÀ PHẦN SỬA LỖI QUAN TRỌNG NHẤT
std::string FtpController::readReply() {
    if (!isConnected()) {
        throw FtpException("Cannot read reply: Not connected.");
    }

    std::string full_reply_message;
    while (true) {
        // Tìm vị trí kết thúc dòng (\r\n) trong bộ đệm
        size_t crlf_pos = control_buffer.find("\r\n");

        // Nếu không tìm thấy, chúng ta cần đọc thêm dữ liệu từ socket
        if (crlf_pos == std::string::npos) {
            char buffer[constants::CHUNK_SIZE];
            int bytes_received = recv(control_socket, buffer, sizeof(buffer), 0);
            
            if (bytes_received <= 0) {
                disconnect();
                throw FtpException("Connection closed by server or recv failed.");
            }
            // Thêm dữ liệu mới vào bộ đệm
            control_buffer.append(buffer, bytes_received);
            continue; // Quay lại vòng lặp để tìm \r\n một lần nữa
        }

        // Nếu đã tìm thấy một dòng hoàn chỉnh
        std::string line = control_buffer.substr(0, crlf_pos);
        // Xóa dòng vừa xử lý và ký tự \r\n khỏi bộ đệm
        control_buffer.erase(0, crlf_pos + 2);

        full_reply_message += line + "\r\n";

        // Kiểm tra xem đây có phải là dòng cuối cùng của một phản hồi FTP không
        // Dòng cuối có dạng: "XXX message" (3 chữ số, 1 dấu cách)
        if (line.length() >= 4 && isdigit(line[0]) && isdigit(line[1]) && isdigit(line[2]) && line[3] == ' ') {
            std::cout << "SERVER < " << full_reply_message;
            return full_reply_message;
        }
    }
}

SOCKET FtpController::createDataConnection() {
    if (!is_passive_mode) {
        throw FtpException("Active mode is not supported in this version.");
    }

    sendCommand("PASV");
    std::string reply = readReply();
    if (reply.rfind("227", 0) != 0) {
        throw FtpException("Server did not enter passive mode. Reply: " + reply);
    }

    size_t start = reply.find('(');
    size_t end = reply.find(')');
    if (start == std::string::npos || end == std::string::npos) {
        throw FtpException("Invalid PASV response format: " + reply);
    }

    std::string data = reply.substr(start + 1, end - start - 1);
    for (char& c : data) { if (c == ',') c = ' '; }
    
    int h1, h2, h3, h4, p1, p2;
    if (sscanf(data.c_str(), "%d %d %d %d %d %d", &h1, &h2, &h3, &h4, &p1, &p2) != 6) {
        throw FtpException("Could not parse PASV response values: " + data);
    }

    std::string pasv_host = std::to_string(h1) + "." + std::to_string(h2) + "." + std::to_string(h3) + "." + std::to_string(h4);
    int pasv_port = p1 * 256 + p2;

    std::cout << "DEBUG: Passive mode details received. Connecting to " << pasv_host << ":" << pasv_port << std::endl;

    SOCKET data_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (data_socket == INVALID_SOCKET) {
        throw FtpException("Failed to create data socket.");
    }

    DWORD timeout = 15000; // 15 giây timeout
    if (setsockopt(data_socket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout)) == SOCKET_ERROR ||
        setsockopt(data_socket, SOL_SOCKET, SO_SNDTIMEO, (const char*)&timeout, sizeof(timeout)) == SOCKET_ERROR) {
        closesocket(data_socket);
        throw FtpException("Failed to set socket timeout options.");
    }

    sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(pasv_port);
    
    if (inet_pton(AF_INET, pasv_host.c_str(), &server_addr.sin_addr) <= 0) {
        closesocket(data_socket);
        throw FtpException("Invalid address received from PASV response: " + pasv_host);
    }

    if (::connect(data_socket, (SOCKADDR*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        int error_code = WSAGetLastError();
        closesocket(data_socket);
        throw FtpException("Failed to connect data socket to " + pasv_host + ":" + std::to_string(pasv_port) + ". WSAError: " + std::to_string(error_code));
    }

    std::cout << "DEBUG: Data connection established." << std::endl;
    return data_socket;
}


// =================================================================
// Public Functions
// =================================================================

bool FtpController::connect(const std::string& host, int port) {
    if (isConnected()) {
        disconnect();
    }
    std::cout << "DEBUG: Attempting to connect to " << host << ":" << port << std::endl;
    addrinfo hints = {}, *res = nullptr;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    if (getaddrinfo(host.c_str(), std::to_string(port).c_str(), &hints, &res) != 0) {
        throw FtpException("getaddrinfo failed for host: " + host);
    }
    control_socket = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (control_socket == INVALID_SOCKET) {
        freeaddrinfo(res);
        throw FtpException("Failed to create control socket.");
    }
    if (::connect(control_socket, res->ai_addr, (int)res->ai_addrlen) == SOCKET_ERROR) {
        closesocket(control_socket);
        control_socket = INVALID_SOCKET;
        freeaddrinfo(res);
        throw FtpException("Failed to connect to server. Check host or firewall.");
    }
    freeaddrinfo(res);
    std::cout << "DEBUG: TCP connection established." << std::endl;
    control_buffer.clear();
    std::string welcome_msg = readReply();
    if (welcome_msg.rfind("220", 0) != 0) {
        disconnect();
        return false;
    }
    this->current_host = host;
    return true;
}

bool FtpController::login(const std::string& user, const std::string& pass) {
    sendCommand("USER " + user);
    std::string user_reply = readReply();
    if (user_reply.rfind("331", 0) != 0) {
        return false;
    }
    sendCommand("PASS " + pass);
    std::string pass_reply = readReply();
    if (pass_reply.rfind("230", 0) == 0) {
        this->current_user = user;
        setTransferMode(TransferMode::BINARY);
        return true;
    }
    return false;
}

void FtpController::disconnect() {
    if (isConnected()) {
        try {
            sendCommand("QUIT");
            readReply();
        } catch (const FtpException&) {
            // Ignore errors on quit
        }
        closesocket(control_socket);
        control_socket = INVALID_SOCKET;
        current_host.clear();
        current_user.clear();
        control_buffer.clear();
    }
}

bool FtpController::isConnected() const {
    return control_socket != INVALID_SOCKET;
}

void FtpController::setTransferMode(TransferMode mode) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand(mode == TransferMode::ASCII ? "TYPE A" : "TYPE I");
    readReply();
    this->current_mode = mode;
}

void FtpController::setPassive(bool is_passive) {
    this->is_passive_mode = is_passive;
}

std::string FtpController::getStatus() {
    if (!isConnected()) {
        return "Not connected.";
    }
    std::string status = "Connected to " + current_host + " as " + current_user + ".\n";
    // --- SỬA LỖI CỘNG CHUỖI Ở ĐÂY ---
    status += std::string("Mode: ") + (current_mode == TransferMode::BINARY ? "Binary" : "ASCII") + ", ";
    status += std::string("Passive: ") + (is_passive_mode ? "On" : "Off") + ".";
    return status;
}