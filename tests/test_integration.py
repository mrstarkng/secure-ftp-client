import subprocess
import time
import os
import shutil
import socket
import sys  # Thêm import sys để lấy đường dẫn python một cách an toàn
import pytest
from pathlib import Path

# Giả sử FTPClientApp nằm trong ftp_client/app.py
# Nếu cấu trúc khác, bạn cần điều chỉnh dòng import này
from ftp_client.app import FTPClientApp

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
    # Sử dụng sys.executable để đảm bảo dùng đúng trình thông dịch python đang chạy test
    cmd = [
        sys.executable, "-m", "clamav_agent.server",
        "--host", "127.0.0.1", "--port", str(port)
    ]
    proc = subprocess.Popen(cmd)
    
    # Chờ một chút để server khởi động
    time.sleep(1) 
    
    yield port # Cung cấp port cho test
    
    # Dọn dẹp sau khi toàn bộ test kết thúc
    proc.terminate()
    proc.wait()

@pytest.fixture(scope="session")
def ftp_server(tmp_path_factory):
    """
    Khởi động một FTP server (dùng pyftpdlib) trên một cổng ngẫu nhiên,
    với một thư mục gốc trống.
    """
    # SỬA LỖI: Bắt đầu với một thư mục server trống để tránh xung đột trạng thái
    ftp_root = tmp_path_factory.mktemp("ftp_root")
    port = get_free_port()
    
    # Lệnh để khởi động FTP server với user/pass và thư mục gốc được chỉ định
    cmd = [
        sys.executable, "-m", "pyftpdlib", "-w",
        "-u", "ftpuser", "-P", "password123",
        "-p", str(port), "--directory", str(ftp_root)
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(1) # Chờ server khởi động
    
    yield ftp_root, port # Cung cấp thư mục gốc và port cho test
    
    # Dọn dẹp
    proc.terminate()
    proc.wait()

def test_integration_e2e(agent_port, ftp_server, tmp_path, monkeypatch):
    """
    Test tích hợp End-to-End cho toàn bộ luồng hoạt động của FTP Client.
    """
    # 1. Chuẩn bị môi trường test
    
    # Lấy thông tin từ fixture của FTP server
    ftp_root, ftp_port = ftp_server

    # "Khỉ vá" (Monkey-patching): Tạm thời thay đổi địa chỉ của Agent trong code client
    # để nó trỏ đến server test đang chạy, mà không cần sửa code gốc.
    import ftp_client.app as app_mod
    monkeypatch.setattr(app_mod, "CLAMAV_AGENT_HOST", "127.0.0.1")
    monkeypatch.setattr(app_mod, "CLAMAV_AGENT_PORT", agent_port)
    
    # Chuẩn bị thư mục làm việc cho client và các file để upload
    client_cwd = tmp_path
    (client_cwd / "clean.txt").write_text("this is a clean file to upload.")
    (client_cwd / "eicar.com.txt").write_text("X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")

    # 2. Khởi tạo client và thực hiện các thao tác
    
    client = FTPClientApp("127.0.0.1", ftp_port, "ftpuser", "password123")
    
    # --- Bắt đầu kiểm thử các chức năng theo một kịch bản logic ---

    # Test 1: Upload file sạch (phải thành công)
    assert client.put(str(client_cwd / "clean.txt")) is True
    assert (ftp_root / "clean.txt").exists()

    # Test 2: Upload file nhiễm virus (phải bị từ chối)
    # Server ban đầu trống, nên nếu upload bị chặn, file sẽ không tồn tại.
    assert client.put(str(client_cwd / "eicar.com.txt")) is False
    assert not (ftp_root / "eicar.com.txt").exists()

    # Test 3: Tải file sạch đã upload thành công ở Test 1
    client.get("clean.txt", str(client_cwd / "downloaded_clean.txt"))
    assert (client_cwd / "downloaded_clean.txt").exists()

    # Test 4: Xóa file sạch trên server
    client.delete("clean.txt")
    assert not (ftp_root / "clean.txt").exists()

    # Test 5: Tạo và xóa thư mục
    client.mkdir("new_folder")
    assert (ftp_root / "new_folder").is_dir()
    client.rmdir("new_folder")
    assert not (ftp_root / "new_folder").exists()

    # 3. Dọn dẹp
    client.close()
