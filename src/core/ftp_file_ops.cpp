#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <fstream>
#include <iostream>
#ifdef _WIN32
#include <windows.h>
#include <codecvt>
#include <locale>

// Helper function to convert UTF-8 to wide string on Windows
std::wstring utf8_to_wide(const std::string& utf8) {
    if (utf8.empty()) return std::wstring();
    
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    if (size_needed == 0) return std::wstring();
    
    std::wstring result(size_needed - 1, 0);
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, &result[0], size_needed);
    return result;
}
#endif

// Helper function to open file with UTF-8 path on Windows
std::ifstream open_ifstream_utf8(const std::string& path) {
#ifdef _WIN32
    return std::ifstream(utf8_to_wide(path).c_str(), std::ios::binary);
#else
    return std::ifstream(path, std::ios::binary);
#endif
}

// Helper function to open file for writing with UTF-8 path on Windows
std::ofstream open_ofstream_utf8(const std::string& path) {
#ifdef _WIN32
    return std::ofstream(utf8_to_wide(path).c_str(), std::ios::binary | std::ios::trunc);
#else
    return std::ofstream(path, std::ios::binary | std::ios::trunc);
#endif
}

bool FtpController::deleteFile(const std::string& remote_path) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    // Send DELE command with conditional quoting for spaces
    std::string dele_command = "DELE " + (remote_path.find(' ') != std::string::npos ? "\"" + remote_path + "\"" : remote_path);
    sendCommand(dele_command);
    std::string reply = readReply();
    int code = parseResponseCode(reply);
    
    if (isSuccessCode(code)) {
        std::cout << "DEBUG: File deleted successfully: " << remote_path << std::endl;
        return true;
    } else {
        std::cout << "ERROR: Failed to delete file. Server reply: " << reply << std::endl;
        return false;
    }
}

bool FtpController::renameFile(const std::string& from, const std::string& to) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    // Send RNFR command with conditional quoting for spaces
    std::string rnfr_command = "RNFR " + (from.find(' ') != std::string::npos ? "\"" + from + "\"" : from);
    sendCommand(rnfr_command);
    std::string rnfr_reply = readReply();
    int rnfr_code = parseResponseCode(rnfr_reply);
    
    if (rnfr_code != 350) {
        std::cout << "ERROR: RNFR failed. Server reply: " << rnfr_reply << std::endl;
        return false;
    }
    
    // Send RNTO command with conditional quoting for spaces
    std::string rnto_command = "RNTO " + (to.find(' ') != std::string::npos ? "\"" + to + "\"" : to);
    sendCommand(rnto_command);
    std::string rnto_reply = readReply();
    int rnto_code = parseResponseCode(rnto_reply);
    
    if (isSuccessCode(rnto_code)) {
        std::cout << "DEBUG: File renamed successfully: " << from << " -> " << to << std::endl;
        return true;
    } else {
        std::cout << "ERROR: RNTO failed. Server reply: " << rnto_reply << std::endl;
        return false;
    }
}

bool FtpController::downloadFile(const std::string& remote, const std::string& local) {
    if (!isConnected()) throw FtpException("Not connected.");

    std::ofstream file = open_ofstream_utf8(local);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for writing: " + local);
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send RETR command with conditional quoting for spaces
        std::string retr_command = "RETR " + (remote.find(' ') != std::string::npos ? "\"" + remote + "\"" : remote);
        sendCommand(retr_command);

        // Read initial response (should be 150 or 125)
        std::string initial_reply = readReply();
        int initial_code = parseResponseCode(initial_reply);
        if (initial_code != 150 && initial_code != 125) {
            closesocket(data_socket);
            throw FtpException("Server did not prepare for file transfer. Reply: " + initial_reply);
        }

        // Read file data from data connection
        char buffer[constants::CHUNK_SIZE];
        int bytes_received;
        size_t total_bytes = 0;
        
        while ((bytes_received = recv(data_socket, buffer, sizeof(buffer), 0)) > 0) {
            file.write(buffer, bytes_received);
            total_bytes += bytes_received;
        }

        // Close data connection
        closesocket(data_socket);
        data_socket = INVALID_SOCKET;
        file.close();

        // Read final response (should be 226)
        std::string final_reply = readReply();
        int final_code = parseResponseCode(final_reply);
        if (final_code != 226) {
            std::cout << "WARNING: Server did not send 226 completion code. Reply: " << final_reply << std::endl;
        }

        std::cout << "DEBUG: Downloaded " << total_bytes << " bytes to " << local << std::endl;
        return true;

    } catch (...) {
        if (data_socket != INVALID_SOCKET) {
            closesocket(data_socket);
        }
        file.close();
        throw;
    }
}

bool FtpController::uploadFile(const std::string& local, const std::string& remote) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    std::ifstream file = open_ifstream_utf8(local);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for reading: " + local);
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send STOR command with conditional quoting for spaces
        std::string stor_command = "STOR " + (remote.find(' ') != std::string::npos ? "\"" + remote + "\"" : remote);
        sendCommand(stor_command);

        // Read initial response (should be 150 or 125)
        std::string initial_reply = readReply();
        int initial_code = parseResponseCode(initial_reply);
        if (initial_code != 150 && initial_code != 125) {
            closesocket(data_socket);
            throw FtpException("Server did not prepare for file transfer. Reply: " + initial_reply);
        }

        // Send file data through data connection
        char buffer[constants::CHUNK_SIZE];
        size_t total_bytes = 0;
        
        while (file.read(buffer, sizeof(buffer)) || file.gcount() > 0) {
            int bytes_to_send = static_cast<int>(file.gcount());
            int bytes_sent = send(data_socket, buffer, bytes_to_send, 0);
            
            if (bytes_sent == SOCKET_ERROR) {
                closesocket(data_socket);
                throw FtpException("Failed to send file data.");
            }
            
            total_bytes += bytes_sent;
        }

        // Close data connection
        closesocket(data_socket);
        data_socket = INVALID_SOCKET;
        file.close();

        // Read final response (should be 226)
        std::string final_reply = readReply();
        int final_code = parseResponseCode(final_reply);
        if (final_code != 226) {
            std::cout << "WARNING: Server did not send 226 completion code. Reply: " << final_reply << std::endl;
        }

        std::cout << "DEBUG: Uploaded " << total_bytes << " bytes from " << local << std::endl;
        return true;

    } catch (...) {
        if (data_socket != INVALID_SOCKET) {
            closesocket(data_socket);
        }
        file.close();
        throw;
    }
}

bool FtpController::uploadFileWithProgress(const std::string& local, const std::string& remote, ProgressCallback callback) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    std::ifstream file = open_ifstream_utf8(local);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for reading: " + local);
    }

    // Get file size for progress tracking
    file.seekg(0, std::ios::end);
    size_t file_size = file.tellg();
    file.seekg(0, std::ios::beg);

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send STOR command with conditional quoting for spaces
        std::string stor_command = "STOR " + (remote.find(' ') != std::string::npos ? "\"" + remote + "\"" : remote);
        sendCommand(stor_command);

        // Read initial response (should be 150 or 125)
        std::string initial_reply = readReply();
        int initial_code = parseResponseCode(initial_reply);
        if (initial_code != 150 && initial_code != 125) {
            closesocket(data_socket);
            throw FtpException("Server did not prepare for file transfer. Reply: " + initial_reply);
        }

        // Send file data through data connection with progress tracking
        char buffer[constants::CHUNK_SIZE];
        size_t total_bytes = 0;
        
        // Initial progress callback
        if (callback) {
            callback(0, file_size);
        }
        
        while (file.read(buffer, sizeof(buffer)) || file.gcount() > 0) {
            int bytes_to_send = static_cast<int>(file.gcount());
            int bytes_sent = send(data_socket, buffer, bytes_to_send, 0);
            
            if (bytes_sent == SOCKET_ERROR) {
                closesocket(data_socket);
                throw FtpException("Failed to send file data.");
            }
            
            total_bytes += bytes_sent;
            
            // Progress callback
            if (callback) {
                callback(total_bytes, file_size);
            }
        }

        // Close data connection
        closesocket(data_socket);
        data_socket = INVALID_SOCKET;
        file.close();

        // Read final response (should be 226)
        std::string final_reply = readReply();
        int final_code = parseResponseCode(final_reply);
        if (final_code != 226) {
            std::cout << "WARNING: Server did not send 226 completion code. Reply: " << final_reply << std::endl;
        }

        // Final progress callback
        if (callback) {
            callback(total_bytes, file_size);
        }

        std::cout << "DEBUG: Uploaded " << total_bytes << " bytes from " << local << std::endl;
        return true;

    } catch (...) {
        if (data_socket != INVALID_SOCKET) {
            closesocket(data_socket);
        }
        file.close();
        throw;
    }
}

bool FtpController::downloadFileWithProgress(const std::string& remote, const std::string& local, ProgressCallback callback) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    std::ofstream file = open_ofstream_utf8(local);
    if (!file.is_open()) {
        throw FtpException("Cannot create local file for writing: " + local);
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send RETR command with conditional quoting for spaces
        std::string retr_command = "RETR " + (remote.find(' ') != std::string::npos ? "\"" + remote + "\"" : remote);
        sendCommand(retr_command);

        // Read initial response (should be 150 or 125)
        std::string initial_reply = readReply();
        int initial_code = parseResponseCode(initial_reply);
        if (initial_code != 150 && initial_code != 125) {
            closesocket(data_socket);
            throw FtpException("Server did not prepare for file transfer. Reply: " + initial_reply);
        }

        // Receive file data through data connection with progress tracking
        char buffer[constants::CHUNK_SIZE];
        size_t total_bytes = 0;
        
        // Initial progress callback (we don't know file size for downloads)
        if (callback) {
            callback(0, 0);
        }
        
        int bytes_received;
        while ((bytes_received = recv(data_socket, buffer, sizeof(buffer), 0)) > 0) {
            file.write(buffer, bytes_received);
            if (file.fail()) {
                closesocket(data_socket);
                throw FtpException("Failed to write to local file.");
            }
            
            total_bytes += bytes_received;
            
            // Progress callback (unknown total size for downloads)
            if (callback) {
                callback(total_bytes, 0);
            }
        }

        if (bytes_received == SOCKET_ERROR) {
            closesocket(data_socket);
            throw FtpException("Failed to receive file data.");
        }

        // Close data connection
        closesocket(data_socket);
        data_socket = INVALID_SOCKET;
        file.close();

        // Read final response (should be 226)
        std::string final_reply = readReply();
        int final_code = parseResponseCode(final_reply);
        if (final_code != 226) {
            std::cout << "WARNING: Server did not send 226 completion code. Reply: " << final_reply << std::endl;
        }

        // Final progress callback
        if (callback) {
            callback(total_bytes, total_bytes);
        }

        std::cout << "DEBUG: Downloaded " << total_bytes << " bytes to " << local << std::endl;
        return true;

    } catch (...) {
        if (data_socket != INVALID_SOCKET) {
            closesocket(data_socket);
        }
        file.close();
        throw;
    }
}