import cmd
from ftp_client.app import FTPClientApp


class CLI(cmd.Cmd):
    intro = "Welcome to Secure FTP Client. Type help or ? to list commands."
    prompt = "ftp> "

    def __init__(self, host, port, user, password):
        super().__init__()
        self.app = FTPClientApp(host, port, user, password)

    def do_ls(self, arg):
        "List directory contents: ls [path]"
        items = self.app.ls(arg or "")
        for item in items:
            print(item)

    def do_cd(self, arg):
        "Change directory: cd <directory>"
        try:
            self.app.cd(arg)
        except Exception as e:
            print(f"Error: {e}")

    def do_pwd(self, arg):
        "Print working directory"
        print(self.app.pwd())

    def do_get(self, arg):
        "Download file: get <remote_path> [local_path]"
        parts = arg.split()
        remote = parts[0]
        local = parts[1] if len(parts) > 1 else None
        try:
            self.app.get(remote, local)
            print("Download complete.")
        except Exception as e:
            print(f"Error: {e}")

    def do_put(self, arg):
        "Upload file: put <local_path> [remote_path]"
        parts = arg.split()
        local = parts[0]
        remote = parts[1] if len(parts) > 1 else None
        try:
            self.app.put(local, remote)
            print("Upload complete.")
        except Exception as e:
            print(f"Error: {e}")

    def do_quit(self, arg):
        "Exit the client"
        print("Goodbye.")
        return True

    def do_exit(self, arg):
        return self.do_quit(arg)
