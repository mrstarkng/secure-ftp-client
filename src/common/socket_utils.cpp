#include "socket_utils.h"
#include <winsock2.h>

WsaInitializer::WsaInitializer() {
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        throw FtpException("WSAStartup failed.");
    }
}

WsaInitializer::~WsaInitializer() {
    WSACleanup();
}

/**
 * @brief Parses the 3-digit response code from an FTP server reply.
 * @param response The full response string from the server.
 * @return The integer response code, or 0 if parsing fails.
 */
int parseResponseCode(const std::string& response) {
    if (response.length() < 3) {
        return 0;
    }
    try {
        return std::stoi(response.substr(0, 3));
    } catch (const std::invalid_argument&) {
        return 0;
    } catch (const std::out_of_range&) {
        return 0;
    }
}

/**
 * @brief Checks if an FTP response code indicates success (2xx).
 * @param code The 3-digit integer response code.
 * @return True if the code is in the 200-299 range, false otherwise.
 */
bool isSuccessCode(int code) {
    return code >= 200 && code < 300;
}