import socket
import re
from pathlib import Path
from tqdm import tqdm
import os

# Lớp ngoại lệ tùy chỉnh để xử lý các lỗi từ server FTP
class FTPError(Exception):
    pass

class FTPHandler:
    """
    Trình xử lý FTP sử dụng socket thô, với logic kiểm tra lỗi phản hồi
    và hỗ trợ upload/download thư mục đệ quy.
    """
    def __init__(self, host, port, user, password):
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.settimeout(10.0)
        try:
            self.control_socket.connect((host, port))
        except (socket.timeout, OSError) as e:
            raise FTPError(f"Không thể kết nối đến server: {e}")
        self.control_socket.settimeout(None)
        self._read_response()
        self._send_command(f"USER {user}")
        resp = self._send_command(f"PASS {password}")
        if not resp.startswith("230"):
            raise FTPError(resp)
        self.set_type('I')
        self.host = host
        self.pwd_path = self.pwd() # Lấy đường dẫn ban đầu

    def _read_response(self, socket_instance=None) -> str:
        sock = socket_instance or self.control_socket
        response = ""
        sock.settimeout(10.0) 
        while True:
            try:
                part = sock.recv(4096).decode('utf-8', errors='ignore')
                if not part:
                    break
                response += part
                lines = response.strip().split('\r\n')
                if len(lines) > 0 and re.match(r'^\d{3} ', lines[-1]):
                    break
            except socket.timeout:
                break
        sock.settimeout(None)
        print(f"S: {response.strip()}")
        return response.strip()

    def _send_command(self, command: str) -> str:
        print(f"C: {command}")
        self.control_socket.sendall(f"{command}\r\n".encode('utf-8'))
        return self._read_response()

    def _open_data_connection(self):
        response = self._send_command("PASV")
        if not response.startswith("227"):
            raise FTPError(response)
        match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', response)
        if not match:
            raise IOError("Không thể phân tích phản hồi PASV.")
        parts = [int(p) for p in match.groups()]
        data_host = ".".join(map(str, parts[:4]))
        data_port = (parts[4] << 8) + parts[5]
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.connect((data_host, data_port))
        return data_socket

    def list(self, path=""):
        data_socket = self._open_data_connection()
        response = self._send_command(f"LIST {path}")
        if not response.startswith(('125', '150')):
            data_socket.close()
            raise FTPError(response)
        listing_data = b""
        while True:
            chunk = data_socket.recv(8192)
            if not chunk:
                break
            listing_data += chunk
        data_socket.close()
        self._read_response()
        return listing_data.decode('utf-8', errors='ignore').strip().split('\r\n')

    def cwd(self, dirname):
        response = self._send_command(f"CWD {dirname}")
        if not response.startswith("250"):
            raise FTPError(response)
        self.pwd_path = self.pwd()

    def pwd(self):
        response = self._send_command("PWD")
        if not response.startswith("257"):
            raise FTPError(response)
        match = re.search(r'"(.*?)"', response)
        if match:
            return match.group(1)
        return "/"

    def get(self, remote_path, local_path=None):
        local = Path(local_path or Path(remote_path).name)
        self.set_type('I')
        size_response = self._send_command(f"SIZE {remote_path}")
        total_size = int(size_response.split()[1]) if size_response.startswith("213") else None
        data_socket = self._open_data_connection()
        response = self._send_command(f"RETR {remote_path}")
        if not response.startswith(('125', '150')):
            data_socket.close()
            raise FTPError(response)
        with open(local, "wb") as f, tqdm(total=total_size, unit="B", unit_scale=True, desc=f"Downloading {local.name}") as pbar:
            while True:
                chunk = data_socket.recv(8192)
                if not chunk: break
                f.write(chunk)
                pbar.update(len(chunk))
        data_socket.close()
        self._read_response()

    def put(self, local_path, remote_path=None):
        path = Path(local_path)
        remote = remote_path or path.name
        size = path.stat().st_size
        self.set_type('I')
        data_socket = self._open_data_connection()
        response = self._send_command(f"STOR {remote}")
        if not response.startswith(('125', '150')):
            data_socket.close()
            raise FTPError(response)
        with open(path, "rb") as f, tqdm(total=size, unit="B", unit_scale=True, desc=f"Uploading {path.name}") as pbar:
            while True:
                chunk = f.read(8192)
                if not chunk: break
                data_socket.sendall(chunk)
                pbar.update(len(chunk))
        data_socket.close()
        self._read_response()

    def put_recursive(self, local_path_str: str):
        local_dir = Path(local_path_str)
        if not local_dir.is_dir():
            raise ValueError(f"{local_dir} không phải là một thư mục.")
        self.mkdir(local_dir.name)
        self.cwd(local_dir.name)
        for item in local_dir.iterdir():
            if item.is_dir():
                self.put_recursive(str(item))
            else:
                self.put(str(item))
        self.cwd("..")

    def get_recursive(self, remote_dir_name: str, local_parent_dir: Path):
        """
        SỬA LỖI: Tải về đệ quy, tái tạo đúng cấu trúc thư mục cục bộ.
        """
        # Tạo thư mục cục bộ tương ứng trong thư mục cha
        current_local_dir = local_parent_dir / remote_dir_name
        current_local_dir.mkdir(exist_ok=True)

        # Di chuyển vào thư mục trên server
        self.cwd(remote_dir_name)
        
        items = self.list()
        for item_info in items:
            if not item_info.strip(): continue
            parts = item_info.split()
            if len(parts) < 9: continue
            name = parts[-1]
            if name in ('.', '..'): continue
            
            is_dir = item_info.startswith('d')

            if is_dir:
                # Gọi đệ quy, truyền vào thư mục cục bộ hiện tại làm cha mới
                self.get_recursive(name, current_local_dir)
            else:
                # Tải file về đúng thư mục cục bộ hiện tại
                self.get(name, str(current_local_dir / name))
        
        # Quay trở lại thư mục cha trên server
        self.cwd("..")

    def delete(self, remote_path):
        response = self._send_command(f"DELE {remote_path}")
        if not response.startswith("250"):
            raise FTPError(response.split(None, 1)[-1])

    def mkdir(self, directory):
        response = self._send_command(f"MKD {directory}")
        if not (response.startswith("257") or "exist" in response):
            raise FTPError(response.split(None, 1)[-1])

    def rmdir(self, directory):
        response = self._send_command(f"RMD {directory}")
        if not response.startswith("250"):
            raise FTPError(response.split(None, 1)[-1])

    def set_type(self, type_code):
        response = self._send_command(f"TYPE {type_code}")
        if not response.startswith("200"):
            raise FTPError(response)

    def status(self):
        response = self._send_command("STAT")
        return response

    def close(self):
        self._send_command("QUIT")
        self.control_socket.close()
