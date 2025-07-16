#include "command_handler.h"
#include "../common/constants.h"
#include <iostream>
#include <vector>
#include <string>
#include <filesystem> // Add for local file system operations

namespace fs = std::filesystem;

CommandHandler::CommandHandler() : av(constants::AGENT_HOST, constants::AGENT_PORT) {}

void CommandHandler::mgetRecursive(const std::string& remote_path, const std::string& local_path) {
    // Ensure local directory exists
    fs::create_directories(local_path);

    // Get directory listing
    std::string list_data = ftp.listDirectory(remote_path);
    auto entries = ftp.parseListOutput(list_data);

    for (const auto& entry : entries) {
        std::string remote_entry_path = remote_path.empty() ? entry.first : remote_path + "/" + entry.first;
        fs::path local_entry_path = fs::path(local_path) / entry.first;

        if (entry.second) { // It's a directory
            std::cout << "Entering directory: " << remote_entry_path << std::endl;
            mgetRecursive(remote_entry_path, local_entry_path.string());
        } else { // It's a file
            std::cout << "Downloading " << remote_entry_path << " to " << local_entry_path.string() << std::endl;
            ftp.downloadFile(remote_entry_path, local_entry_path.string());
        }
    }
}

void CommandHandler::mputRecursive(const fs::path& local_path, const std::string& remote_path) {
    for (const auto& entry : fs::directory_iterator(local_path)) {
        std::string remote_entry_path = remote_path.empty() ? entry.path().filename().string() : remote_path + "/" + entry.path().filename().string();

        if (fs::is_directory(entry.status())) {
            std::cout << "Creating remote directory: " << remote_entry_path << std::endl;
            ftp.makeDirectory(remote_entry_path);
            mputRecursive(entry.path(), remote_entry_path);
        } else if (fs::is_regular_file(entry.status())) {
            std::cout << "Uploading " << entry.path().string() << " to " << remote_entry_path << std::endl;
            // You might want to add ClamAV scan here as well, similar to handle_put
            ftp.uploadFile(entry.path().string(), remote_entry_path);
        }
    }
}

std::string CommandHandler::handle_mget(const std::vector<std::string>& args) {
    if (!ftp.isConnected()) return "Error: Not connected.";
    if (args.empty()) return "Usage: mget <remote_path> [local_path]";

    std::string remote_path = args[0];
    std::string local_path = (args.size() > 1) ? args[1] : ".";

    try {
        mgetRecursive(remote_path, local_path);
        return "Multiple get operation completed.";
    } catch (const FtpException& e) {
        return std::string("Error during mget: ") + e.what();
    } catch (const fs::filesystem_error& e) {
        return std::string("Filesystem error during mget: ") + e.what();
    }
}

std::string CommandHandler::handle_mput(const std::vector<std::string>& args) {
    if (!ftp.isConnected()) return "Error: Not connected.";
    if (args.empty()) return "Usage: mput <local_path> [remote_path]";

    fs::path local_path = args[0];
    std::string remote_path = (args.size() > 1) ? args[1] : "";

    if (!fs::exists(local_path) || !fs::is_directory(local_path)) {
        return "Error: Local path must be an existing directory.";
    }

    try {
        mputRecursive(local_path, remote_path);
        return "Multiple put operation completed.";
    } catch (const FtpException& e) {
        return std::string("Error during mput: ") + e.what();
    } catch (const fs::filesystem_error& e) {
        return std::string("Filesystem error during mput: ") + e.what();
    }
}

std::string CommandHandler::handle_open(const std::vector<std::string>& args) {
    if (args.size() < 3) return "Usage: open <host> <user> <pass>";
    if (ftp.isConnected()) return "Already connected. Use 'close' first.";
    
    try {
        if (ftp.connect(args[0], constants::FTP_DEFAULT_PORT) && ftp.login(args[1], args[2])) {
            return "Successfully connected and logged in.";
        }
    } catch (const FtpException& e) {
        return std::string("Error: ") + e.what();
    }
    return "Failed to connect.";
}

std::string CommandHandler::handle_ls(const std::vector<std::string>& args) {
    if (!ftp.isConnected()) return "Error: Not connected.";
    std::string path = args.empty() ? "" : args[0];
    try {
        return ftp.listDirectory(path);
    } catch (const FtpException& e) {
        return std::string("Error listing directory: ") + e.what();
    }
}

std::string CommandHandler::handle_cd(const std::vector<std::string>& args) {
    if (args.empty()) return "Usage: cd <remote_directory>";
    if (!ftp.isConnected()) return "Error: Not connected.";
    try {
        if (ftp.changeDirectory(args[0])) {
            return "250 Directory successfully changed.";
        }
        return "550 Failed to change directory.";
    } catch (const FtpException& e) {
        return std::string("Error: ") + e.what();
    }
}

std::string CommandHandler::handle_pwd() {
    if (!ftp.isConnected()) return "Error: Not connected.";
    try {
        return ftp.printWorkingDirectory();
    } catch (const FtpException& e) {
        return std::string("Error: ") + e.what();
    }
}

std::string CommandHandler::handle_close() {
    ftp.disconnect();
    return "Disconnected.";
}

std::string CommandHandler::handle_put(const std::vector<std::string>& args) {
    if (args.empty()) return "Usage: put <local_file> [remote_file]";
    if (!ftp.isConnected()) return "Not connected.";

    std::string local_file = args[0];
    std::string remote_file = (args.size() > 1) ? args[1] : local_file;

    try {
        std::cout << "Scanning " << local_file << "..." << std::endl;
        ScanResult result = av.scanFile(local_file);

        if (result == ScanResult::OK) {
            std::cout << "File is clean. Uploading..." << std::endl;
            if (ftp.uploadFile(local_file, remote_file)) {
                return "File uploaded successfully.";
            }
            return "File upload failed.";
        } else if (result == ScanResult::INFECTED) {
            return "WARNING: File is infected! Upload aborted.";
        } else { // SCAN_ERROR
            return "ERROR: Could not scan file. Upload aborted.";
        }
    } catch (const FtpException& e) {
        return std::string("Error: ") + e.what();
    }
}

std::string CommandHandler::handle_quit() {
    handle_close();
    return "Goodbye!";
}

std::string CommandHandler::handle_status() {
    return ftp.getStatus();
}

std::string CommandHandler::handle_passive(const std::vector<std::string>& args) {
    bool is_passive = args.empty() || args[0] != "off";
    ftp.setPassive(is_passive);
    return std::string("Passive mode ") + (is_passive ? "on." : "off.");
}

std::string CommandHandler::handle_binary() {
    ftp.setTransferMode(TransferMode::BINARY);
    return "Transfer mode set to Binary.";
}

std::string CommandHandler::handle_ascii() {
    ftp.setTransferMode(TransferMode::ASCII);
    return "Transfer mode set to ASCII.";
}

std::string CommandHandler::handle_prompt() {
    prompt_mode = !prompt_mode;
    return std::string("Interactive prompting ") + (prompt_mode ? "on." : "off.");
}

std::string CommandHandler::handle_mkdir(const std::vector<std::string>& args) {
    if (args.empty()) return "Usage: mkdir <directory>";
    if (ftp.makeDirectory(args[0])) return "Directory created.";
    return "Failed to create directory.";
}

std::string CommandHandler::handle_rmdir(const std::vector<std::string>& args) {
    if (args.empty()) return "Usage: rmdir <directory>";
    if (ftp.removeDirectory(args[0])) return "Directory removed.";
    return "Failed to remove directory.";
}

std::string CommandHandler::handle_delete(const std::vector<std::string>& args) {
    if (args.empty()) return "Usage: delete <file>";
    if (ftp.deleteFile(args[0])) return "File deleted.";
    return "Failed to delete file.";
}

std::string CommandHandler::handle_rename(const std::vector<std::string>& args) {
    if (args.size() < 2) return "Usage: rename <from> <to>";
    if (ftp.renameFile(args[0], args[1])) return "File renamed.";
    return "Failed to rename file.";
}

std::string CommandHandler::handle_get(const std::vector<std::string>& args) {
    if (args.size() < 2) return "Usage: get <remote_file> <local_file>";
    if (ftp.downloadFile(args[0], args[1])) return "File downloaded.";
    return "Failed to download file.";
}

// =================================================================
// === RECURSIVE IMPLEMENTATIONS SECTION ===
// =================================================================

// =================================================================
// === HÀM BỊ THIẾU ĐƯỢC THÊM VÀO ĐÂY ===
// =================================================================
std::string CommandHandler::handle_help() {
    return R"(
Commands may be abbreviated. Commands are:

ascii         Set ASCII transfer type
binary        Set binary transfer type
bye           Terminate ftp session and exit
cd            Change remote working directory
close         Terminate ftp session
delete        Delete remote file
get           Receive file
help          Print local help information
ls            List contents of remote directory
mget          Get multiple files
mkdir         Make directory on the remote machine
mput          Send multiple files
open          Connect to remote ftp
passive       Enter passive transfer mode
prompt        Toggle interactive prompting on multiple commands
put           Send one file
pwd           Print working directory on remote machine
quit          Same as bye
rename        Rename file
rmdir         Remove directory on the remote machine
status        Show current status
?             Same as help
)";
}