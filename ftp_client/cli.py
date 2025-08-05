import cmd
import glob
from ftp_client.app import FTPClientApp

class CLI(cmd.Cmd):
    intro = "Welcome to Secure FTP Client. Type help or ? to list commands."
    prompt = "ftp> "

    def __init__(self, host, port, user, password):
        super().__init__()
        self.app = FTPClientApp(host, port, user, password)

    def do_ls(self, arg):
        items = self.app.ls(arg or "")
        for item in items:
            print(item)

    def do_cd(self, arg):
        try:
            self.app.cd(arg)
        except Exception as e:
            print(f"Error: {e}")

    def do_pwd(self, arg):
        print(self.app.pwd())

    def do_get(self, arg):
        parts = arg.split()
        remote = parts[0]
        local = parts[1] if len(parts) > 1 else None
        try:
            self.app.get(remote, local)
            print("Download complete.")
        except Exception as e:
            print(f"Error: {e}")

    def do_put(self, arg):
        parts = arg.split()
        local = parts[0]
        remote = parts[1] if len(parts) > 1 else None
        try:
            ok = self.app.put(local, remote)
            print(f"{local}: {'✅ uploaded' if ok else '❌ skipped'}")
        except Exception as e:
            print(f"Error: {e}")

    def do_mput(self, arg):
        files = glob.glob(arg)
        if not files:
            print(f"No files match '{arg}'.")
            return
        for path in files:
            ok = self.app.put(path)
            status = "✅ uploaded" if ok else "❌ skipped"
            print(f"{path}: {status}")

    def do_delete(self, arg):
        "Delete remote file: delete <remote_path>"
        try:
            self.app.delete(arg)
            print(f"{arg}: deleted")
        except Exception as e:
            print(f"Error: {e}")

    def do_mkdir(self, arg):
        "Make remote directory: mkdir <directory>"
        try:
            self.app.mkdir(arg)
            print(f"{arg}: directory created")
        except Exception as e:
            print(f"Error: {e}")

    def do_rmdir(self, arg):
        "Remove remote directory: rmdir <directory>"
        try:
            self.app.rmdir(arg)
            print(f"{arg}: directory removed")
        except Exception as e:
            print(f"Error: {e}")

    def do_ascii(self, arg):
        "Set transfer mode to ASCII"
        try:
            self.app.set_ascii_mode()
            print("Transfer mode: ASCII")
        except Exception as e:
            print(f"Error: {e}")

    def do_binary(self, arg):
        "Set transfer mode to binary"
        try:
            self.app.set_binary_mode()
            print("Transfer mode: binary")
        except Exception as e:
            print(f"Error: {e}")

    def do_quit(self, arg):
        print("Goodbye.")
        return True

    def do_exit(self, arg):
        return self.do_quit(arg)
