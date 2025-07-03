# file: cli_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from session_manager import SessionManager
import threading

class CliWidget(QWidget):
    """Widget giao diện dòng lệnh cho một tab."""
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session = session_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Vùng hiển thị output
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        font = QFont("Consolas", 11)
        self.output_area.setFont(font)
        self.output_area.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4;")
        
        # Dòng nhập lệnh
        self.input_line = QLineEdit()
        self.input_line.setFont(font)
        self.input_line.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4; border: none;")
        
        layout.addWidget(self.output_area)
        layout.addWidget(self.input_line)

        # Kết nối tín hiệu
        self.input_line.returnPressed.connect(self.on_command_entered)
        self.session.output_received.connect(self.append_output)

        self.append_output("Welcome to Secure FTP Client (CLI Mode).\nType 'open <host> <user> <pass>' to connect.")

    def on_command_entered(self):
        command = self.input_line.text()
        if command:
            self.append_output(f"ftp> {command}")
            self.input_line.clear()
            # Chạy lệnh trong một thread riêng để không làm treo UI
            threading.Thread(target=self.session.process_command_line, args=(command,), daemon=True).start()

    def append_output(self, text):
        self.output_area.append(text)
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())