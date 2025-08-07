# ftp_client/cli.py
import cmd
import glob
from pathlib import Path
import fnmatch

# Giả sử FTPClientApp nằm trong ftp_client/app.py
from ftp_client.app import FTPClientApp

class CLI(cmd.Cmd):
    intro = "Welcome to Secure FTP Client. Type help or ? to list commands."
    prompt = "ftp> "

    def __init__(self, host, port, user, password):
        super().__init__()
        try:
            self.app = FTPClientApp(host, port, user, password)
        except Exception as e:
            print(f"Lỗi khởi tạo: {e}")
            self.app = None

    def precmd(self, line):
        if not self.app and not line.strip().startswith(('quit', 'exit', 'help', '?')):
            print("Không thể thực thi lệnh, kết nối ban đầu thất bại.")
            return ""
        return line

    def do_ls(self, arg):
        "Liệt kê file và thư mục trên server. Cú pháp: ls [đường_dẫn]"
        items = self.app.ls(arg or "")
        for item in items:
            print(item)

    def do_cd(self, arg):
        "Thay đổi thư mục làm việc trên server. Cú pháp: cd <tên_thư_mục>"
        if not arg:
            print("Lỗi: Lệnh 'cd' cần một tên thư mục.")
            return
        try:
            self.app.cd(arg)
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_pwd(self, arg):
        "Hiển thị thư mục làm việc hiện tại trên server."
        print(self.app.pwd())

    def do_get(self, arg):
        "Tải về một file hoặc thư mục (đệ quy). Cú pháp: get <đường_dẫn_server> [đường_dẫn_cục_bộ]"
        parts = arg.split()
        if not parts:
            print("Lỗi: Lệnh 'get' cần đường dẫn trên server.")
            return
        remote = parts[0]
        local = parts[1] if len(parts) > 1 else None
        try:
            self.app.get(remote, local)
            print("Tải về hoàn tất.")
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_mget(self, arg):
        "Tải nhiều file từ server (hỗ trợ wildcard, không đệ quy). Cú pháp: mget *.txt"
        if not arg:
            print("Lỗi: Lệnh 'mget' cần một mẫu file (ví dụ: *.txt).")
            return
        
        try:
            full_listing = self.app.ls()
            if not full_listing:
                print("Thư mục trên server trống hoặc không thể truy cập.")
                return

            files_to_download = []
            for item_info in full_listing:
                if not item_info.strip() or item_info.startswith('d'):
                    continue
                file_name = item_info.split()[-1]
                if fnmatch.fnmatch(file_name, arg):
                    files_to_download.append(file_name)

            if not files_to_download:
                print(f"Không tìm thấy file nào trên server khớp với '{arg}'.")
                return

            for file_name in files_to_download:
                print(f"Đang tải về {file_name}...")
                self.app.get(file_name)
            print("Tải về nhiều file hoàn tất.")
        except Exception as e:
            print(f"Lỗi khi thực hiện mget: {e}")

    def do_put(self, arg):
        "Tải lên một file hoặc thư mục (đệ quy và quét virus). Cú pháp: put <đường_dẫn_cục_bộ>"
        parts = arg.split()
        if not parts:
            print("Lỗi: Lệnh 'put' cần đường dẫn cục bộ.")
            return
        local = parts[0]
        # Tham số remote cho put thư mục không được hỗ trợ trong logic này
        remote = parts[1] if len(parts) > 1 else None
        try:
            ok = self.app.put(local, remote)
            print(f"{local}: {'✅ đã tải lên' if ok else '❌ bị từ chối'}")
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_mput(self, arg):
        "Tải nhiều file lên server (hỗ trợ wildcard, không đệ quy). Cú pháp: mput *.txt"
        if not arg:
            print("Lỗi: Lệnh 'mput' cần một mẫu file (ví dụ: *.txt).")
            return
            
        all_paths = glob.glob(arg)
        if not all_paths:
            print(f"Không tìm thấy file nào khớp với '{arg}'.")
            return

        files_to_upload = [p for p in all_paths if Path(p).is_file()]
        if not files_to_upload:
            print(f"Mẫu '{arg}' không khớp với bất kỳ file nào (chỉ có thư mục).")
            return

        for path in files_to_upload:
            try:
                ok = self.app.put(path)
                status = "✅ đã tải lên" if ok else "❌ bị từ chối"
                print(f"{path}: {status}")
            except Exception as e:
                print(f"Lỗi khi tải lên {path}: {e}")

    def do_delete(self, arg):
        "Xóa file trên server. Cú pháp: delete <tên_file>"
        if not arg:
            print("Lỗi: Lệnh 'delete' cần tên file.")
            return
        try:
            self.app.delete(arg)
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_mkdir(self, arg):
        "Tạo thư mục trên server. Cú pháp: mkdir <tên_thư_mục>"
        if not arg:
            print("Lỗi: Lệnh 'mkdir' cần tên thư mục.")
            return
        try:
            self.app.mkdir(arg)
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_rmdir(self, arg):
        "Xóa thư mục trên server. Cú pháp: rmdir <tên_thư_mục>"
        if not arg:
            print("Lỗi: Lệnh 'rmdir' cần tên thư mục.")
            return
        try:
            self.app.rmdir(arg)
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_ascii(self, arg):
        "Đặt chế độ truyền file là ASCII."
        try:
            self.app.set_ascii_mode()
            print("Chế độ truyền file: ASCII")
        except Exception as e:
            print(f"Lỗi: {e}")

    def do_binary(self, arg):
        "Đặt chế độ truyền file là Binary."
        try:
            self.app.set_binary_mode()
            print("Chế độ truyền file: Binary")
        except Exception as e:
            print(f"Lỗi: {e}")
            
    def do_status(self, arg):
        "Hiển thị trạng thái của server."
        status_info = self.app.status()
        print(status_info)

    def do_quit(self, arg):
        "Đóng kết nối và thoát chương trình."
        if self.app:
            self.app.close()
        print("Tạm biệt.")
        return True

    def do_exit(self, arg):
        "Thoát chương trình."
        return self.do_quit(arg)
