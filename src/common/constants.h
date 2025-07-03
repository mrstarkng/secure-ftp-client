#pragma once

namespace constants {
    // Cấu hình cho ClamAV Agent
    constexpr const char* AGENT_HOST = "127.0.0.1";
    constexpr int AGENT_PORT = 9999;

    // Cấu hình mặc định cho FTP
    constexpr int FTP_DEFAULT_PORT = 21;
    constexpr int CHUNK_SIZE = 4096;
}