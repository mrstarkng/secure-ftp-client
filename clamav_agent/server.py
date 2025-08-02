import argparse
import logging
import socket
import struct
import threading
import tempfile
import os
from pathlib import Path
from typing import Tuple

# ─────────────────────────────────── Constants ────────────────────────────────────
BUFFER_SIZE = 8192
DEFAULT_CLAMD_SOCKET = "/opt/homebrew/var/run/clamav/clamd.sock"
DEFAULT_AGENT_PORT = 9000

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

# ──────────────────────────────── ClamAV scanning ───────────────────────────────
def scan_path(tmp_path: Path, clamd_socket: str) -> bool:
    """Scan a file on disk via SCAN command to clamd."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(clamd_socket)
            cmd = f"SCAN {tmp_path.as_posix()}\n".encode()
            s.sendall(cmd)
            response = s.recv(BUFFER_SIZE).decode()
            logging.debug("clamd response (SCAN): %s", response.strip())
            # e.g. "/tmp/tmp123: Eicar-Test-Signature FOUND"
            return not response.strip().endswith("FOUND")
    except Exception as e:
        logging.error("Error SCAN fallback: %s", e)
        return False


def scan_file(data: bytes, clamd_socket: str) -> bool:
    """Fallback scanning: write data to a world-readable temp file, call SCAN."""
    tmp_dir = "/tmp"  # use /tmp for world-accessible tmp dir
    # create temp file in shared temp dir
    with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=".bin") as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        # ensure world-readable
        path.chmod(0o644)
    except Exception:
        pass
    # perform scan
    clean = scan_path(path, clamd_socket)
    # cleanup
    try:
        path.unlink()
    except Exception:
        pass
    return clean

# ───────────────────────────── Socket server & handler ──────────────────────────
def recv_exact(sock: socket.socket, count: int) -> bytes:
    buf = bytearray()
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed while receiving")
        buf.extend(chunk)
    return bytes(buf)


def handle_client(conn: socket.socket, addr: Tuple[str, int], clamd_socket: str):
    logging.info("Client %s connected", addr)
    try:
        header = recv_exact(conn, 4)
        length = struct.unpack("!I", header)[0]
        if length <= 0:
            raise ValueError("Invalid file length")
        data = recv_exact(conn, length)

        clean = scan_file(data, clamd_socket)
        status = b"OK" if clean else b"INFECTED"
        conn.sendall(status + b"\n")
    except Exception as exc:
        logging.error("Handler error for %s: %s", addr, exc)
        try:
            conn.sendall(b"ERROR\n")
        except Exception:
            pass
    finally:
        conn.close()
        logging.info("Connection %s closed", addr)


def start_server(host: str, port: int, clamd_socket: str):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        logging.info("ClamAVAgent listening on %s:%d", host, port)
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr, clamd_socket),
                daemon=True,
            ).start()


def main():
    parser = argparse.ArgumentParser(description="ClamAVAgent – Virus-scanning service (SCAN fallback)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_AGENT_PORT, help="TCP port to listen on")
    parser.add_argument(
        "--clamd-socket",
        default=DEFAULT_CLAMD_SOCKET,
        help="Path to clamd UNIX socket (default: %(default)s)",
    )
    args = parser.parse_args()

    logging.info("Starting ClamAVAgent with SCAN fallback (clamd socket: %s)", args.clamd_socket)
    start_server(args.host, args.port, args.clamd_socket)


if __name__ == "__main__":
    main()
