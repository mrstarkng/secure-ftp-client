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
// Private Helper Functions (Phần quan trọng nhất)
// =================================================================

// Gửi một lệnh đến server và in ra log
void FtpController::sendCommand(const std::string& cmd) {
    if (!isConnected()) {
        throw FtpException("Cannot send command: Not connected.");
    }
    std::cout << "CLIENT > " << cmd << std::endl; // In ra lệnh gửi đi để debug
    std::string full_cmd = cmd + "\r\n";
    if (send(control_socket, full_cmd.c_str(), (int)full_cmd.length(), 0) == SOCKET_ERROR) {
        throw FtpException("Failed to send command to server.");
    }
}

// Đọc phản hồi từ server, xử lý multi-line và in ra log
std::string FtpController::readReply() {
    if (!isConnected()) {
        throw FtpException("Cannot read reply: Not connected.");
    }

    std::string full_response;
    char buffer[constants::CHUNK_SIZE];
    
    // Vòng lặp để đảm bảo đọc hết response, đặc biệt là các response nhiều dòng
    while (true) {
        int bytes_received = recv(control_socket, buffer, sizeof(buffer) - 1, 0);
        if (bytes_received <= 0) {
            // Nếu kết nối bị đóng hoặc có lỗi, ném ra exception
            disconnect();
            throw FtpException("Connection closed by server or recv failed.");
        }
        buffer[bytes_received] = '\0';
        full_response.append(buffer);

        // Kiểm tra xem đã nhận đủ một response hoàn chỉnh chưa.
        // Response nhiều dòng có dạng: "XXX-First line", "XXX-Second line", "XXX Final line"
        // Response một dòng có dạng: "XXX Final line"
        // Chúng ta sẽ dừng khi dòng cuối cùng không có dấu gạch nối sau mã code.
        if (bytes_received >= 4 && full_response.length() >= 4) {
            // Tìm vị trí xuống dòng cuối cùng
            size_t last_crlf = full_response.rfind("\r\n");
            if (last_crlf != std::string::npos && last_crlf > 2) {
                // Tìm vị trí bắt đầu của dòng cuối cùng
                size_t start_of_last_line = full_response.rfind("\r\n", last_crlf - 1);
                if (start_of_last_line == std::string::npos) {
                    start_of_last_line = -2; // Trường hợp chỉ có 1 dòng
                }
                std::string last_line = full_response.substr(start_of_last_line + 2);

                // Nếu dòng cuối có dạng "XXX message" (3 số, 1 dấu cách) thì đó là dòng cuối cùng
                if (last_line.length() >= 4 && isdigit(last_line[0]) && isdigit(last_line[1]) && isdigit(last_line[2]) && last_line[3] == ' ') {
                    break; 
                }
            }
        }
    }
    
    std::cout << "SERVER < " << full_response; // In ra toàn bộ phản hồi để debug
    return full_response;
}

// --- Implement đầy đủ cho createDataConnection ---
SOCKET FtpController::createDataConnection() {
    if (!is_passive_mode) {
        throw FtpException("Active mode is not supported in this version.");
    }

    sendCommand("PASV");
    std::string reply = readReply();
    if (reply.rfind("227", 0) != 0) {
        throw FtpException("Server did not enter passive mode. Reply: " + reply);
    }

    // Phân tích chuỗi "227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)."
    size_t start = reply.find('(');
    size_t end = reply.find(')');
    if (start == std::string::npos || end == std::string::npos) {
        throw FtpException("Invalid PASV response format.");
    }

    std::string data = reply.substr(start + 1, end - start - 1);
    std::replace(data.begin(), data.end(), ',', '.'); // Thay dấu phẩy bằng dấu chấm

    int h1, h2, h3, h4, p1, p2;
    // Dùng sscanf để đọc các số từ chuỗi
    sscanf(data.c_str(), "%d.%d.%d.%d.%d.%d", &h1, &h2, &h3, &h4, &p1, &p2);

    // Server có thể trả về IP của chính nó, nhưng an toàn hơn là dùng lại host đã kết nối
    // std::string pasv_host = std::to_string(h1) + "." + std::to_string(h2) + "." + std::to_string(h3) + "." + std::to_string(h4);
    int pasv_port = p1 * 256 + p2;

    std::cout << "DEBUG: Passive mode details received. Connecting to " << this->current_host << ":" << pasv_port << std::endl;

    // Tạo socket mới và kết nối đến data port
    addrinfo hints = {}, *res = nullptr;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    if (getaddrinfo(this->current_host.c_str(), std::to_string(pasv_port).c_str(), &hints, &res) != 0) {
        throw FtpException("getaddrinfo failed for data connection.");
    }

    SOCKET data_socket = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (data_socket == INVALID_SOCKET) {
        freeaddrinfo(res);
        throw FtpException("Failed to create data socket.");
    }

    if (::connect(data_socket, res->ai_addr, (int)res->ai_addrlen) == SOCKET_ERROR) {
        closesocket(data_socket);
        freeaddrinfo(res);
        throw FtpException("Failed to connect data socket.");
    }

    freeaddrinfo(res);
    std::cout << "DEBUG: Data connection established." << std::endl;
    return data_socket;
}


// =================================================================
// Public Functions (Implement đầy đủ)
// =================================================================

bool FtpController::connect(const std::string& host, int port) {
    if (isConnected()) {
        disconnect();
    }

    std::cout << "DEBUG: Attempting to connect to " << host << ":" << port << std::endl;

    addrinfo hints = {}, *res = nullptr;
    hints.ai_family = AF_INET;       // Chỉ dùng IPv4
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

    // Dùng ::connect để tránh xung đột tên với hàm thành viên FtpController::connect
    if (::connect(control_socket, res->ai_addr, (int)res->ai_addrlen) == SOCKET_ERROR) {
        closesocket(control_socket);
        control_socket = INVALID_SOCKET;
        freeaddrinfo(res);
        throw FtpException("Failed to connect to server. Check host or firewall.");
    }

    freeaddrinfo(res);
    std::cout << "DEBUG: TCP connection established." << std::endl;

    std::string welcome_msg = readReply();
    // Mã 220 là tín hiệu server sẵn sàng
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
    // Mã 331 yêu cầu mật khẩu
    if (user_reply.rfind("331", 0) != 0) {
        std::cout << "DEBUG: Server did not ask for password. Login failed." << std::endl;
        return false;
    }

    sendCommand("PASS " + pass);
    std::string pass_reply = readReply();
    // Mã 230 là đăng nhập thành công
    if (pass_reply.rfind("230", 0) == 0) {
        this->current_user = user;
        // Mặc định chuyển sang chế độ Binary sau khi đăng nhập thành công
        setTransferMode(TransferMode::BINARY);
        return true;
    }
    
    std::cout << "DEBUG: Invalid password or login failed." << std::endl;
    return false;
}

void FtpController::disconnect() {
    if (isConnected()) {
        try {
            sendCommand("QUIT");
            readReply();
        } catch (const FtpException& e) {
            // Bỏ qua lỗi nếu không gửi được lệnh QUIT (ví dụ server đã tự đóng)
            std::cerr << "Note: " << e.what() << " while quitting." << std::endl;
        }
        closesocket(control_socket);
        control_socket = INVALID_SOCKET;
        current_host.clear();
        current_user.clear();
    }
}

bool FtpController::isConnected() const {
    return control_socket != INVALID_SOCKET;
}

void FtpController::setTransferMode(TransferMode mode) {
    if (!isConnected()) throw FtpException("Not connected.");
    if (mode == TransferMode::ASCII) {
        sendCommand("TYPE A");
    } else {
        sendCommand("TYPE I");
    }
    readReply(); // Đọc phản hồi "200 Type set to..."
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
    status += "Mode: " + (current_mode == TransferMode::BINARY ? std::string("Binary") : std::string("ASCII")) + ", ";
    status += "Passive: " + (is_passive_mode ? std::string("On") : std::string("Off")) + ".";
    return status;
}