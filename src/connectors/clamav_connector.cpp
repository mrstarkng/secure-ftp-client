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
    // Temporarily bypass ClamAV scanning and always return OK
    // TODO: Re-enable actual scanning when ClamAV agent is available
    std::cout << "ClamAV scan bypassed for: " << local_file_path << " (returning OK)" << std::endl;
    return ScanResult::OK;
}