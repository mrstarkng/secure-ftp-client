#include "command_handler.h"
#include "../common/constants.h"
#include <iostream>
#include <vector>
#include <string>

CommandHandler::CommandHandler() : av(constants::AGENT_HOST, constants::AGENT_PORT) {}

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
        // SỬA LỖI: Thêm 'return' để trả về kết quả
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
        // SỬA LỖI: Thêm 'return' để trả về kết quả
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

std::string CommandHandler::handle_mget(const std::vector<std::string>& args) {
    return "mget command not implemented yet.";
}

std::string CommandHandler::handle_mput(const std::vector<std::string>& args) {
    return "mput command not implemented yet.";
}

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