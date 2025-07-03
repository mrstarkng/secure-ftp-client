# file: session_manager.py
import ftp_engine # type: ignore
import shlex
from PyQt6.QtCore import QObject, pyqtSignal

class SessionManager(QObject):
    output_received = pyqtSignal(str)
    task_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.client = ftp_engine.FtpClient()
        self.command_map = self._create_command_map()

    def _create_command_map(self):
        # Ánh xạ tên lệnh tới hàm C++ tương ứng
        return {
            "open": self.client.open,
            "close": self.client.close,
            "quit": self.client.quit,
            "bye": self.client.quit,
            "status": self.client.status,
            "passive": self.client.passive, # Đã đổi tên
            "binary": self.client.binary,   # Đã đổi tên
            "ascii": self.client.ascii,     # Đã đổi tên
            "prompt": self.client.prompt,   # Đã đổi tên
            "help": self.client.help,       # Mới thêm
            "?": self.client.help,          # Mới thêm
            "ls": self.client.ls,
            "cd": self.client.cd,
            "pwd": self.client.pwd,
            "mkdir": self.client.mkdir,
            "rmdir": self.client.rmdir,
            "delete": self.client.delete,
            "rename": self.client.rename,
            "get": self.client.get,
            "recv": self.client.get,        # Alias
            "put": self.client.put,
            "mget": self.client.mget,
            "mput": self.client.mput,
        }

    def process_command_line(self, line):
        # ... logic của hàm này không cần thay đổi ...
        if not line.strip():
            return
        try:
            parts = shlex.split(line)
            command_name = parts[0].lower()
            args = parts[1:]
            if command_name in self.command_map:
                # Các hàm không có đối số
                if command_name in ["close", "quit", "bye", "status", "binary", "ascii", "prompt", "pwd", "help", "?"]:
                    result = self.command_map[command_name]()
                else:
                    result = self.command_map[command_name](args)
                
                if result:
                    self.output_received.emit(result)
                if command_name in ["quit", "bye"]:
                    self.task_finished.emit(True, "Session closed.")
            else:
                self.output_received.emit(f"Error: Unknown command '{command_name}'")
        except ftp_engine.FtpException as e:
            self.output_received.emit(f"FTP Error: {e}")
        except Exception as e:
            self.output_received.emit(f"An unexpected error occurred: {e}")