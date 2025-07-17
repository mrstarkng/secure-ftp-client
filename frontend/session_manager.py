# file: session_manager.py
import ftp_engine # type: ignore
import shlex
import queue
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from clamav_installer import get_clamav_path

class SessionManager(QObject):
    output_received = pyqtSignal(str)
    task_finished = pyqtSignal(bool, str)
    scan_failed = pyqtSignal(str, str)  # Signal for scan failure (file_path, reason)
    connected = pyqtSignal()  # Signal when connection is established
    disconnected = pyqtSignal()  # Signal when connection is lost

    def __init__(self):
        super().__init__()
        self.client = ftp_engine.FtpClient()
        self.command_map = self._create_command_map()
        self.command_queue = queue.Queue()
        self.worker_thread = None
        self.stop_worker = threading.Event()

    def start_worker(self):
        """Starts the single worker thread to process commands sequentially."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_worker.clear()
            self.worker_thread = threading.Thread(target=self._command_loop, daemon=True)
            self.worker_thread.start()

    def stop(self):
        """Stops the worker thread and closes the connection."""
        self.stop_worker.set()
        self.command_queue.put(None) # Use a sentinel to unblock queue.get()
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        # Ensure close is called, but don't rely on the thread for it
        try:
            self.client.close()
        except Exception:
            pass
        # Emit disconnected signal
        self.disconnected.emit()
    
    def get_clamav_status(self):
        """Get ClamAV status for display"""
        clamav_path = get_clamav_path()
        if clamav_path:
            if "ClamAV" in clamav_path:
                return "ClamAV: Portable installation active"
            else:
                return "ClamAV: System installation active"
        else:
            return "ClamAV: Not available (uploads will not be scanned)"

    def _command_loop(self):
        """The main loop for the worker thread, executing commands one by one."""
        while not self.stop_worker.is_set():
            try:
                command_line = self.command_queue.get()
                if command_line is None:
                    break
                
                self._execute_single_command(command_line)
                # Emit signal that the task for this command line is done
                self.task_finished.emit(True, command_line.split(' ', 1)[0])
            except Exception as e:
                error_msg = f"Worker thread error: {e}"
                self.output_received.emit(error_msg)
                self.task_finished.emit(False, "error")

    def process_command_line(self, line: str):
        """Public method for the UI to queue a command for execution."""
        if line and line.strip():
            self.command_queue.put(line.strip())

    def _execute_single_command(self, line: str):
        """The actual execution logic, called only by the worker thread."""
        try:
            parts = shlex.split(line)
            command_name = parts[0].lower()
            args = parts[1:]
            
            if command_name in self.command_map:
                if command_name in ["close", "quit", "bye", "status", "binary", "ascii", "prompt", "pwd", "help", "?"]:
                    result = self.command_map[command_name]()
                else:
                    result = self.command_map[command_name](args)
                
                # Check for connection status changes
                if command_name == "open" and result and "Successfully connected" in result:
                    self.connected.emit()
                elif command_name in ["close", "quit", "bye"]:
                    self.disconnected.emit()
                
                if result:
                    self.output_received.emit(result)
                if command_name in ["quit", "bye"]:
                    self.stop_worker.set()
            else:
                self.output_received.emit(f"Error: Unknown command '{command_name}'")
        except ftp_engine.FtpException as e:
            self.output_received.emit(f"FTP Error: {e}")
        except Exception as e:
            self.output_received.emit(f"An unexpected error occurred: {e}")

    def _scan_file_before_upload(self, local_path):
        """Scan file with ClamAV before upload. Returns True if safe to upload, False if infected."""
        try:
            # Use the C++ ClamAV connector to scan the file
            scan_result = self.client.scanFile(local_path)
            
            if scan_result.startswith("INFECTED:"):
                virus_name = scan_result.split(":", 1)[1].strip()
                reason = f"File is infected with: {virus_name}. Upload cancelled."
                self.scan_failed.emit(local_path, reason)
                self.output_received.emit(f"ClamAV ALERT: {reason}")
                return False
            elif scan_result != "OK":
                reason = f"Antivirus scan failed: {scan_result}. Upload cancelled for safety."
                self.scan_failed.emit(local_path, reason)
                self.output_received.emit(f"ClamAV ERROR: {reason}")
                return False
            else:
                self.output_received.emit(f"ClamAV: File {local_path} is clean - proceeding with upload")
                return True
        except Exception as e:
            reason = f"Failed to scan file: {str(e)}. Upload cancelled for safety."
            self.scan_failed.emit(local_path, reason)
            self.output_received.emit(f"ClamAV ERROR: {reason}")
            return False

    def _safe_put(self, args):
        """PUT command with virus scanning"""
        if len(args) < 1:
            return "Error: PUT requires at least a local file path"
        
        local_path = args[0]
        
        # Scan file before upload
        if not self._scan_file_before_upload(local_path):
            return "Upload blocked due to virus scan failure"
        
        # If scan passes, proceed with normal upload
        return self.client.put(args)

    def _safe_mput(self, args):
        """MPUT command with virus scanning for each file"""
        if len(args) < 1:
            return "Error: MPUT requires at least a file pattern"
        
        # For MPUT, we need to handle multiple files
        # This is a simplified version - you might need to expand based on your specific needs
        import glob
        import os
        
        pattern = args[0]
        if os.path.isfile(pattern):
            # Single file
            if not self._scan_file_before_upload(pattern):
                return "Upload blocked due to virus scan failure"
        else:
            # Pattern or directory - scan all matching files
            matching_files = glob.glob(pattern)
            for file_path in matching_files:
                if os.path.isfile(file_path):
                    if not self._scan_file_before_upload(file_path):
                        return f"Upload blocked - infected file found: {file_path}"
        
        # If all scans pass, proceed with normal upload
        return self.client.mput(args)

    def _create_command_map(self):
        # This method remains the same except for put and mput
        return {
            "open": self.client.open, "close": self.client.close, "quit": self.client.quit,
            "bye": self.client.quit, "status": self.client.status, "passive": self.client.passive,
            "binary": self.client.binary, "ascii": self.client.ascii, "prompt": self.client.prompt,
            "help": self.client.help, "?": self.client.help, "ls": self.client.ls, "cd": self.client.cd,
            "pwd": self.client.pwd, "mkdir": self.client.mkdir, "rmdir": self.client.rmdir,
            "delete": self.client.delete, "rename": self.client.rename, "get": self.client.get,
            "recv": self.client.get, "put": self._safe_put, "mget": self.client.mget,
            "mput": self._safe_mput,
        }