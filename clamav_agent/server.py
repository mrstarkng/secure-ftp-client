import argparse
import logging
import socket
import threading

# Import các thành phần cần thiết từ các file khác
from . import config
from . import worker

# ───────────────────────────── Server & Điểm khởi chạy ──────────────────────────

def start_server(host: str, port: int, clamd_socket: str):
    """Khởi tạo và chạy socket server chính."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        logging.info("ClamAVAgent đang lắng nghe trên %s:%d", host, port)
        
        while True:
            conn, addr = server.accept()
            # Tạo một luồng mới để xử lý client, không làm block vòng lặp chính
            client_thread = threading.Thread(
                target=worker.handle_client,
                args=(conn, addr, clamd_socket),
                daemon=True,
            )
            client_thread.start()

def main():
    """Phân tích tham số dòng lệnh và khởi động server."""
    parser = argparse.ArgumentParser(description="ClamAVAgent – Dịch vụ quét virus (sử dụng SCAN fallback)")
    parser.add_argument("--host", default="0.0.0.0", help="Địa chỉ để bind (mặc định: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=config.DEFAULT_AGENT_PORT, help="Cổng TCP để lắng nghe")
    parser.add_argument(
        "--clamd-socket",
        default=config.DEFAULT_CLAMD_SOCKET,
        help="Đường dẫn đến UNIX socket của clamd (mặc định: %(default)s)",
    )
    args = parser.parse_args()

    # Khởi tạo logging từ config
    # Dòng này đảm bảo logging được thiết lập trước khi bất kỳ log nào được ghi
    config.logging

    logging.info("Khởi động ClamAVAgent với SCAN fallback (clamd socket: %s)", args.clamd_socket)
    start_server(args.host, args.port, args.clamd_socket)

if __name__ == "__main__":
    main()
