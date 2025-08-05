# ftp_client/ftp/handler.py
from ftplib import FTP
from pathlib import Path
from tqdm import tqdm

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
        """
        Download a file from the FTP server with a progress bar.
        """
        local = local_path or Path(remote_path).name
        # Try to get remote file size for progress bar
        try:
            total = self.ftp.size(remote_path)
        except Exception:
            total = None

        with open(local, "wb") as f:
            if total:
                pbar = tqdm(total=total, unit="B", unit_scale=True, desc=f"Downloading {remote_path}")
                def callback(data):
                    f.write(data)
                    pbar.update(len(data))
                self.ftp.retrbinary(f"RETR {remote_path}", callback)
                pbar.close()
            else:
                # Fallback without progress bar
                self.ftp.retrbinary(f"RETR {remote_path}", f.write)

    def put(self, local_path, remote_path=None):
        """
        Upload a file to the FTP server with a progress bar.
        """
        path = Path(local_path)
        remote = remote_path or path.name
        size = path.stat().st_size

        with open(path, "rb") as f:
            pbar = tqdm(total=size, unit="B", unit_scale=True, desc=f"Uploading {remote}")
            def callback(data):
                pbar.update(len(data))
            # storbinary reads from file and calls callback after each block
            self.ftp.storbinary(f"STOR {remote}", f, callback=callback)
            pbar.close()

    def delete(self, remote_path):
        self.ftp.delete(remote_path)

    def mkdir(self, directory):
        self.ftp.mkd(directory)

    def rmdir(self, directory):
        self.ftp.rmd(directory)

    def set_type(self, type_code):
        # 'A' for ASCII, 'I' for binary (image)
        self.ftp.voidcmd(f"TYPE {type_code}")

    def close(self):
        self.ftp.quit()
