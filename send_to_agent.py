# save as send_to_agent.py
import socket, struct, pathlib, sys

HOST, PORT = "localhost", 9000
file_path   = pathlib.Path(sys.argv[1]).expanduser()

data = file_path.read_bytes()
length = struct.pack("!I", len(data))

with socket.create_connection((HOST, PORT)) as s:
    s.sendall(length + data)
    result = s.recv(32).decode().strip()
    print("Scan result:", result)

