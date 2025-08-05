import logging
import socket
import struct
import tempfile
from pathlib import Path
from typing import Tuple

# Import các hằng số từ file config
# Giả sử các file này nằm trong cùng một package/thư mục
from . import config

# ──────────────────────────────── Logic Quét Virus ───────────────────────────────

def scan_path(tmp_path: Path, clamd_socket: str) -> bool:
    """Quét một file trên đĩa thông qua lệnh SCAN đến clamd."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(clamd_socket)
            cmd = f"SCAN {tmp_path.as_posix()}\n".encode()
            s.sendall(cmd)
            response = s.recv(config.BUFFER_SIZE).decode()
            logging.debug("Phản hồi từ clamd (SCAN): %s", response.strip())
            return not response.strip().endswith("FOUND")
    except Exception as e:
        logging.error("Lỗi khi quét với SCAN fallback: %s", e)
        return False

def scan_file(data: bytes, clamd_socket: str) -> bool:
    """
    Phương án quét dự phòng: ghi dữ liệu vào một file tạm có quyền đọc công khai,
    sau đó gọi lệnh SCAN.
    """
    tmp_dir = "/tmp"  # Sử dụng thư mục tạm có thể ghi bởi mọi user
    with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=".bin") as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        path.chmod(0o644)
    except Exception:
        pass
    
    clean = scan_path(path, clamd_socket)
    
    try:
        path.unlink()
    except Exception:
        pass
    return clean

# ───────────────────────────── Logic Xử lý Client ──────────────────────────

def recv_exact(sock: socket.socket, count: int) -> bytes:
    """Đọc chính xác 'count' bytes từ socket."""
    buf = bytearray()
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise ConnectionError("Socket đã đóng khi đang nhận dữ liệu")
        buf.extend(chunk)
    return bytes(buf)

def handle_client(conn: socket.socket, addr: Tuple[str, int], clamd_socket: str):
    """Xử lý một client kết nối đến: đọc độ dài, quét, và trả lời."""
    logging.info("Client %s đã kết nối", addr)
    try:
        header = recv_exact(conn, 4)
        (length,) = struct.unpack("!I", header)
        
        # Coi file có độ dài 0 là sạch
        if length == 0:
            conn.sendall(b"OK\n")
            return
        if length < 0:
            conn.sendall(b"ERROR\n")
            return

        data = recv_exact(conn, length)
        clean = scan_file(data, clamd_socket)
        status = b"OK" if clean else b"INFECTED"
        conn.sendall(status + b"\n")
    except Exception as exc:
        logging.error("Lỗi handler cho %s: %s", addr, exc)
        try:
            conn.sendall(b"ERROR\n")
        except Exception:
            pass  # Bỏ qua nếu không thể gửi lỗi (kết nối đã mất)
    finally:
        conn.close()
        logging.info("Kết nối %s đã đóng", addr)
