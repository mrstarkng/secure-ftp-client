import logging

# ─────────────────────────────────── Constants & Config ────────────────────────────────────

# Kích thước buffer cho việc đọc socket
BUFFER_SIZE = 8192

# Đường dẫn mặc định đến UNIX socket của clamd
DEFAULT_CLAMD_SOCKET = "/opt/homebrew/var/run/clamav/clamd.sock"

# Cổng TCP mặc định mà Agent sẽ lắng nghe
DEFAULT_AGENT_PORT = 9000

# Cấu hình logging cơ bản cho toàn bộ ứng dụng
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
