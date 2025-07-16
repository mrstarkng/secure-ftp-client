#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <iostream>
#include <sstream>
#include <vector>

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
        // Re-throw the exception to be handled by the caller
        throw;
    }
}

/**
 * @brief Parses the output of the FTP LIST command.
 * @param list_data The raw string data from the LIST command.
 * @return A vector of pairs, where each pair contains a filename and a boolean
 *         indicating if it's a directory (true) or a file (false).
 * @note This is a basic parser and may not work for all FTP server formats.
 */
std::vector<std::pair<std::string, bool>> FtpController::parseListOutput(const std::string& list_data) {
    std::vector<std::pair<std::string, bool>> result;
    std::stringstream ss(list_data);
    std::string line;

    while (std::getline(ss, line)) {
        // Trim trailing \r
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) continue;

        // Simple check: if the line starts with 'd', it's a directory.
        bool is_directory = (line[0] == 'd');
        
        // Find the last space to get the filename
        size_t last_space = line.rfind(' ');
        if (last_space != std::string::npos) {
            std::string filename = line.substr(last_space + 1);
            // Ignore '.' and '..' entries
            if (filename != "." && filename != "..") {
                result.push_back({filename, is_directory});
            }
        }
    }
    return result;
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
    std::string reply = readReply();
    int code = parseResponseCode(reply);
    
    if (isSuccessCode(code)) {
        std::cout << "DEBUG: Changed directory to: " << path << std::endl;
        return true;
    } else {
        std::cout << "ERROR: Failed to change directory. Server reply: " << reply << std::endl;
        return false;
    }
}

bool FtpController::makeDirectory(const std::string& path) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    sendCommand("MKD " + path);
    std::string reply = readReply();
    int code = parseResponseCode(reply);
    
    if (isSuccessCode(code)) {
        std::cout << "DEBUG: Created directory: " << path << std::endl;
        return true;
    } else {
        std::cout << "ERROR: Failed to create directory. Server reply: " << reply << std::endl;
        return false;
    }
}

bool FtpController::removeDirectory(const std::string& path) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    // First, try to just remove the directory directly (in case it's empty)
    sendCommand("RMD " + path);
    std::string reply = readReply();
    int code = parseResponseCode(reply);
    
    if (isSuccessCode(code)) {
        std::cout << "DEBUG: Removed directory: " << path << std::endl;
        return true;
    }
    
    // If direct removal failed, try recursive deletion
    std::cout << "DEBUG: Directory not empty, attempting recursive deletion of: " << path << std::endl;
    
    // Save current directory
    std::string pwd_cmd_result = printWorkingDirectory();
    std::string current_dir = "";
    
    // Parse the PWD response to get current directory
    size_t start = pwd_cmd_result.find("\"");
    size_t end = pwd_cmd_result.rfind("\"");
    if (start != std::string::npos && end != std::string::npos && start < end) {
        current_dir = pwd_cmd_result.substr(start + 1, end - start - 1);
    }
    
    // Change to the directory we want to delete
    if (!changeDirectory(path)) {
        std::cout << "ERROR: Could not change to directory: " << path << std::endl;
        return false;
    }
    
    // Get directory listing
    std::string list_data;
    try {
        list_data = listDirectory("");
    } catch (const FtpException& e) {
        std::cout << "ERROR: Failed to list directory contents: " << e.what() << std::endl;
        changeDirectory(current_dir); // Try to go back to original directory
        return false;
    }
    
    // Parse the listing
    auto entries = parseListOutput(list_data);
    
    // Delete all files and subdirectories
    for (const auto& entry : entries) {
        const std::string& name = entry.first;
        bool is_dir = entry.second;
        
        if (is_dir) {
            // Recursively delete subdirectory
            removeDirectory(name);
        } else {
            // Delete file
            if (!deleteFile(name)) {
                std::cout << "WARNING: Failed to delete file: " << name << std::endl;
            }
        }
    }
    
    // Go back to parent directory
    if (!changeDirectory("..")) {
        std::cout << "ERROR: Could not change back to parent directory" << std::endl;
        if (!current_dir.empty()) {
            changeDirectory(current_dir); // Try to go back to original directory
        }
        return false;
    }
    
    // Now try to remove the directory again
    sendCommand("RMD " + path);
    reply = readReply();
    code = parseResponseCode(reply);
    
    if (isSuccessCode(code)) {
        std::cout << "DEBUG: Successfully removed directory: " << path << std::endl;
        
        // Return to original directory if we saved it
        if (!current_dir.empty() && current_dir != ".") {
            changeDirectory(current_dir);
        }
        
        return true;
    } else {
        std::cout << "ERROR: Failed to remove directory after recursive deletion. Server reply: " << reply << std::endl;
        
        // Return to original directory if we saved it
        if (!current_dir.empty() && current_dir != ".") {
            changeDirectory(current_dir);
        }
        
        return false;
    }
}