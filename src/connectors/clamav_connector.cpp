#include "clamav_connector.h"
#include "../common/socket_utils.h"
#include "../common/constants.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <cstdlib>
#include <memory>
#include <stdexcept>
#include <sstream>
#include <filesystem>
#include <algorithm>

#ifdef _WIN32
#include <windows.h>
#endif

ClamavConnector::ClamavConnector() {}

std::string ClamavConnector::findClamscanExecutable() {
#ifdef _WIN32
    // Check portable installation in project root first
    std::string current_dir = std::filesystem::current_path().string();
    std::vector<std::string> project_portable_paths = {
        current_dir + "\\clamav-portable\\clamscan.exe",
        current_dir + "\\clamav-portable\\clamav-1.4.3.win.x64\\clamscan.exe"
    };
    
    for (const auto& path : project_portable_paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // Check portable installation in user directory (legacy location)
    std::string localAppData = std::getenv("LOCALAPPDATA") ? std::getenv("LOCALAPPDATA") : "C:\\";
    std::string user_portable_path = localAppData + "\\ClamAV\\clamscan.exe";
    if (std::filesystem::exists(user_portable_path)) {
        return user_portable_path;
    }
    
    // Common installation paths for ClamAV on Windows
    std::vector<std::string> possible_paths = {
        "C:\\Program Files\\ClamAV\\clamscan.exe",
        "C:\\Program Files (x86)\\ClamAV\\clamscan.exe"
    };
    
    for (const auto& path : possible_paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // If not found in common locations, try PATH
    return "clamscan";
#else
    // Check portable installation in project root first
    std::string current_dir = std::filesystem::current_path().string();
    std::vector<std::string> project_portable_paths = {
        current_dir + "/clamav-portable/usr/bin/clamscan",
        current_dir + "/clamav-portable/bin/clamscan"
    };
    
    for (const auto& path : project_portable_paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // Check portable installation in user directory (legacy location)
    std::string home = std::getenv("HOME") ? std::getenv("HOME") : "/tmp";
    std::vector<std::string> user_portable_paths = {
        home + "/ClamAV/usr/bin/clamscan",
        home + "/ClamAV/bin/clamscan"
    };
    
    for (const auto& path : user_portable_paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // Check system-wide installations
    std::vector<std::string> system_paths = {
        "/usr/bin/clamscan",
        "/usr/local/bin/clamscan"
    };
    
    for (const auto& path : system_paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // On Linux/macOS, assume it's in PATH
    return "clamscan";
#endif
}

std::string ClamavConnector::executeScan(const std::string& clamscan_path, const std::string& file_path) {
    // Determine the directory containing clamscan.exe to find the database
    std::filesystem::path clamav_dir = std::filesystem::path(clamscan_path).parent_path();
    std::string db_path = (clamav_dir / "database").string();
    std::string clamscan_path_str = clamscan_path;

#ifdef _WIN32
    // Replace backslashes with forward slashes for executable path only (for command-line compatibility)
    std::replace(clamscan_path_str.begin(), clamscan_path_str.end(), '\\', '/');
#endif

    // Check if database directory exists and has content (use original path for filesystem operations)
    if (!std::filesystem::exists(db_path) || std::filesystem::is_empty(db_path)) {
        std::cout << "DEBUG: ClamAV database not found or empty at: " << db_path << std::endl;
        return "ERROR: ClamAV database not found or empty. Please update virus definitions.";
    }

    // Build command: clamscan --no-summary --infected <file_path>
    // ClamAV will use its default database location
    std::ostringstream command_stream;
    command_stream << "\"" << clamscan_path_str << "\" --no-summary --infected \"" << file_path << "\"";
    
    std::string command = command_stream.str();
    std::cout << "DEBUG: Executing ClamAV command: " << command << std::endl;
    
#ifdef _WIN32
    // On Windows, wrap the entire command in another set of quotes to handle paths with spaces correctly.
    command = "\"" + command + "\"";
    // Use _popen on Windows
    FILE* pipe = _popen(command.c_str(), "r");
#else
    // Use popen on Unix-like systems
    FILE* pipe = popen(command.c_str(), "r");
#endif
    
    if (!pipe) {
        return "ERROR: Failed to execute ClamAV command";
    }
    
    std::string result;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        result += buffer;
    }
    
#ifdef _WIN32
    int return_code = _pclose(pipe);
#else
    int return_code = pclose(pipe);
#endif
    
    // ClamAV exit codes: 0 (clean), 1 (infected), 2+ (error)
    if (return_code == 1) { // Virus found
        // Parse virus name from output
        if (!result.empty()) {
            // Output format: "filename: virusname FOUND"
            size_t colon_pos = result.find(':');
            if (colon_pos != std::string::npos) {
                std::string virus_part = result.substr(colon_pos + 1);
                size_t found_pos = virus_part.find(" FOUND");
                if (found_pos != std::string::npos) {
                    std::string virus_name = virus_part.substr(0, found_pos);
                    // Trim whitespace more robustly
                    virus_name.erase(0, virus_name.find_first_not_of(" \t\n\r"));
                    virus_name.erase(virus_name.find_last_not_of(" \t\n\r") + 1);
                    if (!virus_name.empty()) {
                        return "INFECTED: " + virus_name;
                    }
                }
            }
            
            // Alternative parsing for different output formats
            // Look for pattern like "virusname FOUND" anywhere in the output
            size_t found_pos = result.find(" FOUND");
            if (found_pos != std::string::npos) {
                // Work backwards from " FOUND" to find the virus name
                std::string before_found = result.substr(0, found_pos);
                
                // Look for the last space or colon before the virus name
                size_t name_start = before_found.find_last_of(": \t");
                if (name_start != std::string::npos) {
                    std::string virus_name = before_found.substr(name_start + 1);
                    // Trim whitespace
                    virus_name.erase(0, virus_name.find_first_not_of(" \t\n\r"));
                    virus_name.erase(virus_name.find_last_not_of(" \t\n\r") + 1);
                    if (!virus_name.empty()) {
                        return "INFECTED: " + virus_name;
                    }
                } else {
                    // If no delimiter found, take the whole part before FOUND
                    std::string virus_name = before_found;
                    virus_name.erase(0, virus_name.find_first_not_of(" \t\n\r"));
                    virus_name.erase(virus_name.find_last_not_of(" \t\n\r") + 1);
                    if (!virus_name.empty()) {
                        return "INFECTED: " + virus_name;
                    }
                }
            }
        }
        return "INFECTED: Unknown virus";
    } else if (return_code != 0) { // An error occurred
        // Log the error output from clamscan for debugging
        std::string error_msg = "ERROR: ClamAV scan failed with exit code " + std::to_string(return_code);
        if (!result.empty()) {
            // Sanitize result to avoid overly long error messages
            std::string detailed_error = result;
            // Remove newlines and carriage returns
            detailed_error.erase(std::remove(detailed_error.begin(), detailed_error.end(), '\n'), detailed_error.end());
            detailed_error.erase(std::remove(detailed_error.begin(), detailed_error.end(), '\r'), detailed_error.end());
            if (detailed_error.length() > 200) {
                detailed_error = detailed_error.substr(0, 200) + "...";
            }
            error_msg += ". Details: " + detailed_error;
        }
        return error_msg;
    }
    
    return "OK";
}

std::string ClamavConnector::scanFile(const std::string& local_file_path) {
    // Check if file exists
    if (!std::filesystem::exists(local_file_path)) {
        return "ERROR: File not found: " + local_file_path;
    }
    
    // Find ClamAV executable
    std::string clamscan_path = findClamscanExecutable();
    std::cout << "DEBUG: Using ClamAV executable: " << clamscan_path << std::endl;
    
    // Execute scan
    try {
        std::string result = executeScan(clamscan_path, local_file_path);
        std::cout << "DEBUG: ClamAV scan result: " << result << std::endl;
        return result;
    } catch (const std::exception& e) {
        return "ERROR: " + std::string(e.what());
    }
}