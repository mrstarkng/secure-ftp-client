# file: session_manager.py
import ftp_engine # type: ignore
import shlex
import queue
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class SessionManager(QObject):
    output_received = pyqtSignal(str)
    task_finished = pyqtSignal(bool, str)

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

    def _create_command_map(self):
        # This method remains the same
        return {
            "open": self.client.open, "close": self.client.close, "quit": self.client.quit,
            "bye": self.client.quit, "status": self.client.status, "passive": self.client.passive,
            "binary": self.client.binary, "ascii": self.client.ascii, "prompt": self.client.prompt,
            "help": self.client.help, "?": self.client.help, "ls": self.client.ls, "cd": self.client.cd,
            "pwd": self.client.pwd, "mkdir": self.client.mkdir, "rmdir": self.client.rmdir,
            "delete": self.client.delete, "rename": self.client.rename, "get": self.client.get,
            "recv": self.client.get, "put": self.client.put, "mget": self.client.mget,
            "mput": self.client.mput,
        }