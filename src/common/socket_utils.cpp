#include "socket_utils.h"
#include <winsock2.h>

// Link với thư viện WinSock
#pragma comment(lib, "Ws2_32.lib")

WsaInitializer::WsaInitializer() {
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        throw FtpException("WSAStartup failed.");
    }
}

WsaInitializer::~WsaInitializer() {
    WSACleanup();
}