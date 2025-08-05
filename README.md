# Secure FTP Client with Virus Scanning

A Python-based secure FTP client that integrates with a ClamAV scanning agent to prevent infected files from being uploaded. It supports standard FTP operations, virus pre-scan, progress bars, bulk uploads, and extended commands.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)

   * [Command Reference](#command-reference)
7. [Testing](#testing)
8. [Development & Contributing](#development--contributing)
9. [License](#license)

---

## Project Overview

This project delivers a CLI-based FTP client with built-in virus scanning. Before uploading any file (`put`, `mput`), the client sends the file to a locally running ClamAVAgent which scans via the ClamAV daemon (`clamd`). Only files that pass the scan (`OK`) are uploaded; infected files are automatically blocked.

The solution is comprised of three components:

* **Secure FTP Client** (`ftp_client/`): Python CLI using `ftplib`, extended commands, and scan integration.
* **ClamAVAgent** (`clamav_agent/server.py`): TCP service that accepts file streams, writes to `/tmp`, and SCANs via `clamd` UNIX socket.
* **Test FTP Server**: Localizable by `pyftpdlib` or any standard FTP server (vsftpd, sftpcloud.io).

---

## Architecture

```text
+-------------------+          +-----------------+          +-----------------+
|   FTP Client CLI  | <TCP>    |   ClamAVAgent   | <Unix>   |     clamd       |
|  (scan-before-put)| -------- | (SCAN fallback) | -------- |   (ClamAVd)     |
|                   |          |                 |          |                 |
+-------------------+          +-----------------+          +-----------------+
       |
       | FTP commands (21)
       v
+-------------------+
|  FTP Server Root  |
|  (pyftpdlib /     |
|   vsftpd / remote)|
+-------------------+
```

---

## Features

* **Standard FTP Commands**: `ls`, `cd`, `pwd`, `get`, `put`
* **Extended Commands**: `mput`, `delete`, `mkdir`, `rmdir`, `ascii`, `binary`
* **Virus Pre-Scan**: All uploads scanned by ClamAVAgent before storing
* **Progress Bars**: Real-time upload/download progress using `tqdm`
* **Bulk Upload (`mput`)**: Glob-pattern file selection with per-file feedback
* **Robust Error Handling**: Graceful fallbacks and clear user messages
* **Automated Tests**: Unit tests with mocking, end-to-end integration tests with `pyftpdlib` and ClamAVAgent

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourorg/secure-ftp-client.git
   cd secure-ftp-client
   ```
2. Create a Python virtual environment and activate:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Install and configure ClamAV on macOS M1:

   ```bash
   brew install clamav
   sudo cp /opt/homebrew/etc/clamav/freshclam.conf.sample /opt/homebrew/etc/clamav/freshclam.conf
   sudo cp /opt/homebrew/etc/clamav/clamd.conf.sample    /opt/homebrew/etc/clamav/clamd.conf
   sudo mkdir -p /opt/homebrew/var/{lib,run}/clamav
   sudo freshclam
   sudo brew services start clamav
   ```

---

## Configuration

* **ClamAVAgent**: Adjust socket path or port in `clamav_agent/server.py` or via CLI flags:

  ```bash
  python -m clamav_agent.server --port 9000 --clamd-socket /opt/homebrew/var/run/clamav/clamd.sock
  ```
* **FTP Server**: For local testing, run:

  ```bash
  python3 -m pyftpdlib -w -u ftpuser -P password123 -d ./ftp_root
  ```

---

## Usage

1. **Start ClamAVAgent**:

   ```bash
   python -m clamav_agent.server --port 9000
   ```
2. **Start FTP Server** (local test):

   ```bash
   python3 -m pyftpdlib -w -u ftpuser -P password123 -d ./ftp_root
   ```
3. **Run FTP Client**:

   ```bash
   python -m ftp_client --host localhost --port 2121 --user ftpuser --pass password123
   ```

### Command Reference

| Command             | Description                          |
| ------------------- | ------------------------------------ |
| `ls [path]`         | List remote directory contents       |
| `cd <dir>`          | Change remote directory              |
| `pwd`               | Print remote working directory       |
| `get <rem> [local]` | Download file                        |
| `put <loc> [rem]`   | Upload single file (with virus scan) |
| `mput <pattern>`    | Upload multiple files matching glob  |
| `delete <rem>`      | Remove remote file                   |
| `mkdir <dir>`       | Create remote directory              |
| `rmdir <dir>`       | Remove remote directory              |
| `ascii`             | Set ASCII transfer mode              |
| `binary`            | Set binary transfer mode             |
| `quit` / `exit`     | Exit the client                      |

---

## Testing

* **Unit Tests**:

  ```bash
  pytest -q
  ```
* **Integration Tests**:

  ```bash
  pytest tests/test_integration_e2e.py -q
  ```

---

## Development & Contributing

1. Fork the repository and create a feature branch.
2. Write tests before new features/bugs.
3. Ensure existing tests pass and update `README.md` as needed.
4. Submit a Pull Request with clear description.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
