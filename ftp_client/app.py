# ftp_client/app.py
import socket
import struct
from pathlib import Path

# Import handler và lớp exception mới
from ftp_client.ftp.handler import FTPHandler, FTPError


CLAMAV_AGENT_HOST = "localhost"
CLAMAV_AGENT_PORT = 9000
BUFFER_SIZE = 8192

class FTPClientApp:
    def __init__(self, host, port, user, password):
        self.handler = FTPHandler(host, port, user, password)

    def _handle_error(self, e):
        """Hàm trợ giúp để xử lý lỗi một cách nhất quán."""
        if isinstance(e, BrokenPipeError):
            print(f"Lỗi kết nối: {e}. Kết nối đến server có thể đã bị mất.")
            self.handler = None
        else:
            print(f"Lỗi: {e}")

    def ls(self, path=""):
        try:
            return self.handler.list(path)
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)
            return []

    def cd(self, directory):
        try:
            self.handler.cwd(directory)
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)

    def pwd(self):
        try:
            return self.handler.pwd()
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)
            return "Connection lost."

    def get(self, remote_path, local_path=None):
        """
        Tải về một file hoặc một thư mục.
        Tự động phát hiện và gọi hàm đệ quy nếu cần.
        """
        try:
            # Logic để kiểm tra xem remote_path có phải là thư mục không.
            # Chúng ta thử thay đổi thư mục vào đó. Nếu thành công, nó là thư mục.
            original_pwd = self.handler.pwd()
            is_directory = False
            try:
                self.handler.cwd(remote_path)
                self.handler.cwd(original_pwd) # Quay trở lại ngay lập tức
                is_directory = True
            except FTPError:
                is_directory = False

            if is_directory:
                print(f"'{remote_path}' là một thư mục. Bắt đầu tải về đệ quy...")
                # Nếu người dùng không chỉ định đường dẫn cục bộ, tạo một thư mục cùng tên
                local_parent_dir = Path(local_path or ".").resolve()
                self.handler.get_recursive(remote_path, local_parent_dir)
            else:
                self.handler.get(remote_path, local_path)
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)

    def put(self, local_path, remote_path=None) -> bool:
        """
        Tải lên một file hoặc một thư mục.
        Tự động phát hiện và gọi hàm đệ quy nếu cần.
        Mọi file đều được quét virus.
        """
        path = Path(local_path)
        if not path.exists():
            print(f"Lỗi: Đường dẫn cục bộ '{local_path}' không tồn tại.")
            return False

        if path.is_dir():
            print(f"'{local_path}' là một thư mục. Bắt đầu tải lên đệ quy...")
            return self._put_recursive_scanned(path)
        else:
            return self._put_single_file_scanned(path, remote_path)

    def _put_single_file_scanned(self, local_file: Path, remote_path=None) -> bool:
        """Hàm nội bộ để quét và tải lên một file duy nhất."""
        data = local_file.read_bytes()
        
        try:
            with socket.create_connection((CLAMAV_AGENT_HOST, CLAMAV_AGENT_PORT), timeout=10) as sock:
                header = struct.pack("!I", len(data))
                sock.sendall(header + data)
                result = sock.recv(BUFFER_SIZE).decode().strip()
        except Exception as e:
            print(f"Lỗi kết nối đến ClamAVAgent: {e}")
            return False
            
        if result != "OK":
            print(f"CẢNH BÁO: File {local_file.name} bị phát hiện chứa mã độc. Đã hủy tải lên.")
            return False
            
        try:
            print(f"File {local_file.name} sạch. Bắt đầu tải lên...")
            self.handler.put(str(local_file), remote_path)
            return True
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)
            return False

    def _put_recursive_scanned(self, local_dir: Path) -> bool:
        """Hàm nội bộ để xử lý logic upload đệ quy với quét virus."""
        try:
            # Tạo thư mục gốc trên server
            self.handler.mkdir(local_dir.name)
            self.handler.cwd(local_dir.name)

            for item in local_dir.iterdir():
                if item.is_dir():
                    # Gọi đệ quy cho thư mục con
                    self._put_recursive_scanned(item)
                else:
                    # Gọi hàm tải file đơn (đã bao gồm quét virus)
                    self._put_single_file_scanned(item)
            
            # Quay trở lại thư mục cha
            self.handler.cwd("..")
            return True
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)
            return False

    def delete(self, remote_path):
        try:
            self.handler.delete(remote_path)
            print(f"'{remote_path}' đã được xóa.")
        except (BrokenPipeError, FTPError, ValueError) as e:
            self._handle_error(e)

    def mkdir(self, directory):
        try:
            self.handler.mkdir(directory)
            print(f"Thư mục '{directory}' đã được tạo.")
        except (BrokenPipeError, FTPError, ValueError) as e:
            self._handle_error(e)

    def rmdir(self, directory):
        try:
            self.handler.rmdir(directory)
            print(f"Thư mục '{directory}' đã được xóa.")
        except (BrokenPipeError, FTPError, ValueError) as e:
            self._handle_error(e)

    def set_ascii_mode(self):
        try:
            self.handler.set_type('A')
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)

    def set_binary_mode(self):
        try:
            self.handler.set_type('I')
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)

    def status(self):
        try:
            return self.handler.status()
        except (BrokenPipeError, FTPError) as e:
            self._handle_error(e)
            return "Không thể lấy trạng thái. Mất kết nối."

    def close(self):
        if self.handler:
            try:
                self.handler.close()
            except (BrokenPipeError, FTPError):
                pass
            self.handler = None
