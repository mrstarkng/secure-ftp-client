from ftp_client.ftp.handler import FTPHandler


class FTPClientApp:
    def __init__(self, host, port, user, password):
        self.handler = FTPHandler(host, port, user, password)

    def ls(self, path=""):
        return self.handler.list(path)

    def cd(self, directory):
        self.handler.cwd(directory)

    def pwd(self):
        return self.handler.pwd()

    def get(self, remote_path, local_path=None):
        self.handler.get(remote_path, local_path)

    def put(self, local_path, remote_path=None):
        self.handler.put(local_path, remote_path)

    def close(self):
        self.handler.close()
