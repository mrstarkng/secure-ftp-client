#include "clamav_connector.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <fstream>
#include <vector>
#include <iostream>

ClamavConnector::ClamavConnector(const std::string& agent_host, int agent_port)
    : host(agent_host), port(agent_port) {}

ScanResult ClamavConnector::scanFile(const std::string& local_file_path) {
    std::ifstream file(local_file_path, std::ios::binary);
    if (!file.is_open()) {
        throw FtpException("Cannot open local file for scanning: " + local_file_path);
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        throw FtpException("Failed to create socket for AV agent.");
    }

    sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    inet_pton(AF_INET, host.c_str(), &server_addr.sin_addr);

    if (connect(sock, (SOCKADDR*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        closesocket(sock);
        throw FtpException("Failed to connect to ClamAV agent.");
    }

    char buffer[constants::CHUNK_SIZE];
    while (file.read(buffer, sizeof(buffer)) || file.gcount() > 0) {
        if (send(sock, buffer, file.gcount(), 0) == SOCKET_ERROR) {
            closesocket(sock);
            throw FtpException("Failed to send file data to agent.");
        }
    }

    // Báo cho server biết đã gửi xong
    shutdown(sock, SD_SEND);

    std::string response;
    int bytes_received;
    while ((bytes_received = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[bytes_received] = '\0';
        response += buffer;
    }

    closesocket(sock);

    if (response == "OK") {
        return ScanResult::OK;
    } else if (response == "INFECTED") {
        return ScanResult::INFECTED;
    } else {
        return ScanResult::SCAN_ERROR;
    }
}