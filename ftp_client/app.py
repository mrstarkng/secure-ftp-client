import socket
import struct
import glob
from pathlib import Path
from ftp_client.ftp.handler import FTPHandler

CLAMAV_AGENT_HOST = "localhost"
CLAMAV_AGENT_PORT = 9000
BUFFER_SIZE = 8192

class FTPClientApp:
    def __init__(self, host, port, user, password):
        self.handler = FTPHandler(host, port, user, password)

    def ls(self, path=""):
        return self.handler.list(path)

    def cd(self, directory):
        self.handler.cwd(directory)

    def pwd(self):
        return self.handler.pwd()

    def get(self, remote_path, local_path=None):
        self.handler.get(remote_path, local_path)

    def put(self, local_path, remote_path=None) -> bool:
        path = Path(local_path)
        if not path.exists():
            print(f"Local file {local_path} not found.")
            return False
        data = path.read_bytes()
        try:
            with socket.create_connection((CLAMAV_AGENT_HOST, CLAMAV_AGENT_PORT), timeout=10) as sock:
                header = struct.pack("!I", len(data))
                sock.sendall(header + data)
                result = sock.recv(BUFFER_SIZE).decode().strip()
        except Exception as e:
            print(f"Error connecting to ClamAVAgent: {e}")
            return False
        if result != "OK":
            return False
        self.handler.put(local_path, remote_path)
        return True

    def delete(self, remote_path):
        self.handler.delete(remote_path)

    def mkdir(self, directory):
        self.handler.mkdir(directory)

    def rmdir(self, directory):
        self.handler.rmdir(directory)

    def set_ascii_mode(self):
        self.handler.set_type('A')

    def set_binary_mode(self):
        self.handler.set_type('I')

    def close(self):
        self.handler.close()
