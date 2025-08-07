import pytest
from unittest.mock import MagicMock
from ftp_client.cli import CLI
from ftp_client.app import FTPClientApp

# Lớp giả lập để thay thế FTPHandler trong các bài test đơn vị
class DummyHandler:
    def __init__(self, *args, **kwargs):
        pass
    def list(self, path=""): return ["file1.txt", "dir1"]
    def cd(self, path): pass
    def pwd(self): return "/home/user"
    def get(self, r, l=None): pass
    def put(self, l, r=None): return True
    def delete(self, r): pass
    def mkdir(self, d): pass
    def rmdir(self, d): pass
    def close(self): pass

# Fixture để khởi tạo môi trường test
@pytest.fixture
def setup_env(monkeypatch):
    # "Vá" FTPHandler để nó không thực hiện kết nối mạng thật
    monkeypatch.setattr('ftp_client.app.FTPHandler', DummyHandler)
    # Trả về một instance của handler giả để có thể dùng nếu cần
    return DummyHandler()

# --- Bắt đầu các bài test ---

def test_cli_ls(capsys, setup_env):
    handler = setup_env
    cli = CLI('h', 21, 'u', 'p')
    cli.do_ls('')
    captured = capsys.readouterr()
    assert captured.out.strip() == "file1.txt\ndir1"

def test_cli_pwd(capsys, setup_env):
    handler = setup_env
    cli = CLI('h', 21, 'u', 'p')
    cli.do_pwd('')
    captured = capsys.readouterr()
    assert captured.out.strip() == "/home/user"

def test_cli_mput_outputs(monkeypatch, capsys, setup_env):
    handler = setup_env
    cli = CLI('h', 21, 'u', 'p')
    
    # Vá hàm app.put để trả về True cho 'good.txt' và False cho 'bad.txt'
    def mock_put(path, remote=None):
        # Chuyển path thành chuỗi để kiểm tra an toàn
        return 'good' in str(path)
    cli.app.put = mock_put
    
    # Vá hàm glob để trả về một danh sách file giả
    monkeypatch.setattr('glob.glob', lambda pattern: ['good.txt', 'bad.txt'])
    
    # SỬA LỖI: Thêm phần vá cho is_file để nó luôn coi các mục là file
    monkeypatch.setattr('pathlib.Path.is_file', lambda self: True)
    
    cli.do_mput('*.txt')
    captured = capsys.readouterr().out.strip().splitlines()
    
    assert captured == [
        'good.txt: ✅ đã tải lên',
        'bad.txt: ❌ bị từ chối'
    ]

def test_cli_put_and_delete(monkeypatch, capsys, setup_env):
    handler = setup_env
    cli = CLI('h', 21, 'u', 'p')
    
    # Vá hàm app.put để luôn trả về True
    cli.app.put = lambda path, remote=None: True
    
    cli.do_put('file.txt')
    
    assert capsys.readouterr().out.strip() == 'file.txt: ✅ đã tải lên'

def test_cli_mput_skips_directories(monkeypatch, capsys, setup_env):
    handler = setup_env
    cli = CLI('h', 21, 'u', 'p')
    
    # Giả lập rằng app.put không bao giờ được gọi
    cli.app.put = MagicMock()
    
    # Vá glob để trả về một thư mục
    monkeypatch.setattr('glob.glob', lambda pattern: ['some_dir'])
    # Vá is_file để trả về False cho thư mục
    monkeypatch.setattr('pathlib.Path.is_file', lambda self: False)
    
    cli.do_mput('*')
    
    # Đảm bảo hàm put không được gọi
    cli.app.put.assert_not_called()
    captured = capsys.readouterr().out.strip()
    assert "không khớp với bất kỳ file nào" in captured
