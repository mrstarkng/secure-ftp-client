#include "ftp_controller.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <fstream>
#include <iostream>

bool FtpController::deleteFile(const std::string& remote_path) {
    if (!isConnected()) throw FtpException("Not connected.");
    
    sendCommand("DELE " + remote_path);
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
    
    // Send RNFR command
    sendCommand("RNFR " + from);
    std::string rnfr_reply = readReply();
    int rnfr_code = parseResponseCode(rnfr_reply);
    
    if (rnfr_code != 350) {
        std::cout << "ERROR: RNFR failed. Server reply: " << rnfr_reply << std::endl;
        return false;
    }
    
    // Send RNTO command
    sendCommand("RNTO " + to);
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

    std::ofstream file(local, std::ios::binary | std::ios::trunc);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for writing: " + local);
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send RETR command
        sendCommand("RETR " + remote);

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
    
    std::ifstream file(local, std::ios::binary);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for reading: " + local);
    }

    SOCKET data_socket = INVALID_SOCKET;
    try {
        // Ensure binary mode for file transfers
        setTransferMode(TransferMode::BINARY);

        // Create data connection
        data_socket = createDataConnection();
        
        // Send STOR command
        sendCommand("STOR " + remote);

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