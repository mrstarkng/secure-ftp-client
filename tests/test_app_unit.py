import socket
import struct
import pytest
import sys
from pathlib import Path
from ftp_client.app import FTPClientApp
from ftp_client.cli import CLI

# Dummy FTPHandler to capture calls
class DummyHandler:
    def __init__(self):
        self.actions = []
    def put(self, local_path, remote_path=None):
        self.actions.append(('put', local_path, remote_path))
    def delete(self, remote_path):
        self.actions.append(('delete', remote_path))
    def mkdir(self, directory):
        self.actions.append(('mkdir', directory))
    def rmdir(self, directory):
        self.actions.append(('rmdir', directory))
    def set_type(self, type_code):
        self.actions.append(('type', type_code))
    def close(self):
        self.actions.append(('close', None))
    def list(self, path=""):
        return []
    def cwd(self, directory):
        pass
    def pwd(self):
        return '/'
    def get(self, remote, local=None):
        pass

# Fake socket for ClamAVAgent
class FakeSocket:
    def __init__(self, response_bytes):
        self._response = response_bytes
    def sendall(self, data):
        pass
    def recv(self, bufsize):
        return self._response
    def __enter__(self): return self
    def __exit__(self, *args): pass

@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    # create files
    (tmp_path / 'good.txt').write_text('clean')
    (tmp_path / 'bad.txt').write_text('malware')
    monkeypatch.chdir(tmp_path)
    # patch handler in app
    dummy = DummyHandler()
    monkeypatch.setattr('ftp_client.app.FTPHandler', lambda *args, **kwargs: dummy)
    return dummy

def test_delete_mkdir_rmdir_types_and_close(monkeypatch, setup_env):
    handler = setup_env
    app = FTPClientApp('h',21,'u','p')
    app.delete('file.txt')
    app.mkdir('dir')
    app.rmdir('dir')
    app.set_ascii_mode()
    app.set_binary_mode()
    app.close()
    assert handler.actions == [
        ('delete','file.txt'),
        ('mkdir','dir'),
        ('rmdir','dir'),
        ('type','A'),
        ('type','I'),
        ('close',None)
    ]

def test_put_clean_and_skip(monkeypatch, setup_env):
    handler = setup_env
    app = FTPClientApp('h',21,'u','p')
    # clean
    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs: FakeSocket(b'OK\n'))
    assert app.put('good.txt') is True
    assert handler.actions == [('put','good.txt', None)]
    handler.actions.clear()
    # infected
    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs: FakeSocket(b'INFECTED\n'))
    assert app.put('bad.txt') is False
    assert handler.actions == []

# Test CLI mput output
def test_cli_mput_outputs(monkeypatch, capsys, setup_env):
    handler = setup_env
    cli = CLI('h',21,'u','p')
    # patch app.put to return True for good.txt, False for bad.txt
    cli.app.put = lambda path, remote=None: path == 'good.txt'
    # patch glob
    monkeypatch.setattr('glob.glob', lambda pattern: ['good.txt','bad.txt'])
    cli.do_mput('*.txt')
    captured = capsys.readouterr().out.strip().splitlines()
    assert captured == [
        'good.txt: ✅ uploaded',
        'bad.txt: ❌ skipped'
    ]

# Test put and get CLI commands
def test_cli_put_and_delete(monkeypatch, capsys, setup_env):
    handler = setup_env
    cli = CLI('h',21,'u','p')
    # patch app.put
    cli.app.put = lambda path, remote=None: True
    cli.do_put('file.txt')
    assert capsys.readouterr().out.strip() == 'file.txt: ✅ uploaded'
    # test delete error case
    handler.actions.clear()
    cli.app.delete = lambda path: (_ for _ in ()).throw(Exception('err'))
    cli.do_delete('file.txt')
    assert 'Error: err' in capsys.readouterr().out
