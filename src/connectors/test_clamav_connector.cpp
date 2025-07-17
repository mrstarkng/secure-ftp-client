#include "clamav_connector.h"
#include "../common/constants.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <filesystem>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

ClamavConnector::ClamavConnector() {}

// This is the main method that will be called to scan a file.
// It now connects to the Python agent via a socket.
std::string ClamavConnector::scanFile(const std::string& local_file_path) {
    if (!std::filesystem::exists(local_file_path)) {
        return "ERROR: File not found: " + local_file_path;
    }

    std::ifstream file(local_file_path, std::ios::binary);
    if (!file.is_open()) {
        return "ERROR: Could not open local file: " + local_file_path;
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        return "ERROR: Failed to create socket.";
    }

    sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(constants::CLAMAV_AGENT_PORT); // Using constant for port
    if (inet_pton(AF_INET, constants::CLAMAV_AGENT_HOST, &server_addr.sin_addr) <= 0) {
        closesocket(sock);
        return "ERROR: Invalid address for ClamAV agent.";
    }

    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        closesocket(sock);
        return "ERROR: Failed to connect to ClamAV agent. Is it running?";
    }

    // Send file contents
    char buffer[constants::CHUNK_SIZE];
    while (file.good()) {
        file.read(buffer, sizeof(buffer));
        std::streamsize bytes_read = file.gcount();
        if (bytes_read > 0) {
            if (send(sock, buffer, (int)bytes_read, 0) == SOCKET_ERROR) {
                closesocket(sock);
                return "ERROR: Failed to send file data to agent.";
            }
        }
    }
    file.close();

    // Signal end of file by shutting down the send part of the socket
#ifdef _WIN32
    shutdown(sock, SD_SEND);
#else
    shutdown(sock, SHUT_WR);
#endif

    // Receive result from agent
    std::string result;
    int bytes_received;
    while ((bytes_received = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[bytes_received] = '\0';
        result.append(buffer);
    }

    closesocket(sock);

    if (result.empty()) {
        return "ERROR: No response from ClamAV agent.";
    }

    return result;
}