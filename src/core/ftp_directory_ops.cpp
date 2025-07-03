#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <iostream>

std::string FtpController::listDirectory(const std::string& path) {
    if (!isConnected()) {
        throw FtpException("Not connected.");
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // 1. Mở data connection
        data_socket = createDataConnection();

        // 2. Gửi lệnh LIST
        std::string command = "LIST";
        if (!path.empty()) {
            command += " " + path;
        }
        sendCommand(command);

        // 3. Đọc phản hồi ban đầu trên control connection (phải là 1xx)
        std::string initial_reply = readReply();
        if (initial_reply.rfind("150", 0) != 0 && initial_reply.rfind("125", 0) != 0) {
            closesocket(data_socket);
            throw FtpException("Server did not prepare for file transfer. Reply: " + initial_reply);
        }

        // 4. Đọc toàn bộ dữ liệu từ data connection
        std::string directory_data;
        char buffer[constants::CHUNK_SIZE];
        int bytes_received;
        while ((bytes_received = recv(data_socket, buffer, sizeof(buffer), 0)) > 0) {
            directory_data.append(buffer, bytes_received);
        }

        // 5. Đóng data connection
        closesocket(data_socket);
        data_socket = INVALID_SOCKET;
        std::cout << "DEBUG: Data connection closed." << std::endl;

        // 6. Đọc phản hồi cuối cùng trên control connection (phải là 226)
        std::string final_reply = readReply();
        if (final_reply.rfind("226", 0) != 0) {
            // Đây không phải lỗi nghiêm trọng, chỉ là cảnh báo
            std::cout << "WARNING: Server did not send 226 completion code. Reply: " << final_reply << std::endl;
        }

        return directory_data;

    } catch (const FtpException& e) {
        if (data_socket != INVALID_SOCKET) {
            closesocket(data_socket);
        }
        // Ném lại lỗi để lớp cao hơn xử lý
        throw;
    }
}

std::string FtpController::printWorkingDirectory() {
    if (!isConnected()) {
        throw FtpException("Not connected.");
    }
    sendCommand("PWD");
    std::string reply = readReply();
    // Phản hồi thường có dạng "257 \"/\" is the current directory."
    // Chúng ta có thể phân tích để lấy ra đường dẫn, hoặc chỉ trả về toàn bộ reply.
    return reply;
}

bool FtpController::changeDirectory(const std::string& path) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand("CWD " + path);
    // ... kiểm tra response code ...
    return true;
}

bool FtpController::makeDirectory(const std::string& path) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand("MKD " + path);
    // ... kiểm tra response code ...
    return true;
}

bool FtpController::removeDirectory(const std::string& path) {
    if (!isConnected()) throw FtpException("Not connected.");
    sendCommand("RMD " + path);
    // ... kiểm tra response code ...
    return true;
}