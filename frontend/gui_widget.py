# file: gui_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont  # <--- THÊM DÒNG NÀY
from PyQt6.QtCore import Qt
from session_manager import SessionManager # Thêm import này nếu cần

class GuiWidget(QWidget):
    """Widget giao diện đồ họa cho một tab."""
    def __init__(self, session_manager: SessionManager): # Thêm kiểu dữ liệu cho session_manager
        super().__init__()
        self.session = session_manager
        
        layout = QVBoxLayout(self)
        label = QLabel("Đây là giao diện đồ họa (GUI Mode).\n(Chưa được implement)")
        
        # Bây giờ QFont đã được định nghĩa
        font = QFont("Segoe UI", 14)
        label.setFont(font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # TODO: Thêm các widget như QTreeWidget cho cây thư mục, các nút bấm...
        # Kết nối các nút bấm với các hàm trong self.session
        # Ví dụ: self.upload_button.clicked.connect(self.on_upload_clicked)