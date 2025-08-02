import os


class Config:
    HOST = os.getenv("FTP_HOST", "localhost")
    PORT = int(os.getenv("FTP_PORT", 21))
    USER = os.getenv("FTP_USER", "anonymous")
    PASS = os.getenv("FTP_PASS", "")