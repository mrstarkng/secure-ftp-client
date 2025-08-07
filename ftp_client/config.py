# ftp_client/config.py

import os


class Config:
    HOST = os.getenv("FTP_HOST", "localhost")
    PORT = int(os.getenv("FTP_PORT", 2121))
    USER = os.getenv("FTP_USER", "anonymous")
    PASS = os.getenv("FTP_PASS", "")


# ftp_client/ftp/handler.py
from ftplib import FTP
from pathlib import Path

class FTPHandler:
    def __init__(self, host, port, user, password):
        self.ftp = FTP()
        self.ftp.connect(host, port)
        self.ftp.login(user, password)

    def list(self, path=""):
        return self.ftp.nlst(path)

    def cwd(self, dirname):
        self.ftp.cwd(dirname)

    def pwd(self):
        return self.ftp.pwd()

    def get(self, remote_path, local_path=None):
        local = local_path or Path(remote_path).name
        with open(local, "wb") as f:
            self.ftp.retrbinary(f"RETR {remote_path}", f.write)

    def put(self, local_path, remote_path=None):
        path = Path(local_path)
        remote = remote_path or path.name
        with open(path, "rb") as f:
            self.ftp.storbinary(f"STOR {remote}", f)

    def close(self):
        self.ftp.quit()
