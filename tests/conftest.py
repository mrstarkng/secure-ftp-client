import sys
import warnings
from pathlib import Path
import pytest
import socket
import subprocess
import time
import io

# --- Cấu hình chung cho Pytest ---

# Đảm bảo thư mục gốc của dự án nằm trong sys.path để có thể import
# các module như 'ftp_client' từ thư mục 'tests'.
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

# Bỏ qua các cảnh báo về cấu hình không xác định của pytest
warnings.filterwarnings(
    "ignore",
    category=pytest.PytestConfigWarning,
    message="Unknown config option: python_paths"
)

# --- Xử lý cảnh báo resource_tracker một cách an toàn và triệt để ---
@pytest.fixture(scope="session", autouse=True)
def suppress_resource_tracker_warning():
    """
    Fixture tự động chạy để chặn cảnh báo 'resource_tracker' khi tắt.
    Kỹ thuật này tạo một lớp wrapper đơn giản để lọc stderr một cách an toàn.
    """
    original_stderr = sys.stderr

    class StderrWrapper:
        def __init__(self, original):
            self.original = original

        def write(self, s):
            # Lọc bỏ thông báo không mong muốn
            if "resource_tracker: There appear to be" in s:
                return
            # Ghi tất cả các thông báo khác ra luồng gốc
            try:
                self.original.write(s)
            except ValueError:
                # Bỏ qua lỗi "I/O operation on closed file"
                # có thể xảy ra ở giai đoạn tắt cuối cùng.
                pass

        def flush(self):
            try:
                self.original.flush()
            except ValueError:
                pass

    # Thay thế stderr bằng phiên bản đã được lọc của chúng ta
    sys.stderr = StderrWrapper(original_stderr)
    
    # Cho phép các bài test chạy
    yield
    
    # Khôi phục lại stderr gốc sau khi phiên test kết thúc
    sys.stderr = original_stderr


# --- Các Fixture dùng chung ---

def get_free_port():
    """Trả về một cổng TCP trống được hệ điều hành cấp phát."""
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture(scope="session")
def agent_port():
    """
    Khởi động ClamAVAgent trên một cổng ngẫu nhiên và cung cấp cổng đó cho test.
    Fixture này sẽ chạy một lần cho toàn bộ phiên test.
    """
    port = get_free_port()
    cmd = [
        sys.executable, "-m", "clamav_agent.server",
        "--host", "127.0.0.1", "--port", str(port)
    ]
    # Chuyển hướng output của subprocess để tránh xung đột
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1) 
    yield port
    proc.terminate()
    proc.wait()

@pytest.fixture(scope="session")
def ftp_server(tmp_path_factory):
    """
    Khởi động một FTP server (dùng pyftpdlib) trên một cổng ngẫu nhiên,
    với một thư mục gốc trống.
    """
    ftp_root = tmp_path_factory.mktemp("ftp_root")
    port = get_free_port()
    cmd = [
        sys.executable, "-m", "pyftpdlib", "-w",
        "-u", "ftpuser", "-P", "password123",
        "-p", str(port), "--directory", str(ftp_root)
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    yield ftp_root, port
    proc.terminate()
    proc.wait()
