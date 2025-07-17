#pragma once
#include <string>

// Enum to represent scan result
enum class ScanResult { OK, INFECTED, SCAN_ERROR };

class ClamavConnector {
public:
    // Constructor - no longer needs host/port since we're calling ClamAV directly
    ClamavConnector();

    // Main function to scan file directly using ClamAV executable
    std::string scanFile(const std::string& local_file_path);

private:
    // Find ClamAV executable path
    std::string findClamscanExecutable();
    
    // Execute ClamAV scan command and parse result
    std::string executeScan(const std::string& clamscan_path, const std::string& file_path);
};