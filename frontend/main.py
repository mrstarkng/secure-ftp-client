# file: main.py
import sys
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton, QMenu, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

# Import các widget và session manager
from session_manager import SessionManager
from cli_widget import CliWidget
from gui_widget import GuiWidget

# --- Sao chép các DLLs cần thiết vào cùng thư mục với main.py ---
# libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll
# Và file ftp_engine...pyd

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Session FTP Client")
        self.setGeometry(100, 100, 900, 700)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        self.setCentralWidget(self.tab_widget)

        # Nút "New Tab"
        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setFixedSize(24, 24)
        self.tab_widget.setCornerWidget(self.add_tab_button, Qt.Corner.TopLeftCorner)
        
        # Tạo menu cho nút "+"
        menu = QMenu(self)
        new_cli_action = QAction("New CLI Session", self)
        new_gui_action = QAction("New GUI Session", self)
        menu.addAction(new_cli_action)
        menu.addAction(new_gui_action)
        self.add_tab_button.setMenu(menu)

        # Kết nối action với hàm tạo tab
        new_cli_action.triggered.connect(self.add_cli_tab)
        new_gui_action.triggered.connect(self.add_gui_tab)

        # Tạo tab đầu tiên
        self.add_cli_tab()

    def add_cli_tab(self):
        """Tạo một tab mới với giao diện dòng lệnh."""
        session = SessionManager()
        cli_widget = CliWidget(session)
        
        # Lưu session vào widget để không bị garbage collect
        cli_widget.setProperty("session_manager", session)
        
        index = self.tab_widget.addTab(cli_widget, "CLI Session")
        self.tab_widget.setCurrentIndex(index)

    def add_gui_tab(self):
        """Tạo một tab mới với giao diện đồ họa."""
        session = SessionManager()
        gui_widget = GuiWidget(session)
        gui_widget.setProperty("session_manager", session)
        
        index = self.tab_widget.addTab(gui_widget, "GUI Session")
        self.tab_widget.setCurrentIndex(index)

    def close_tab(self, index):
        """Đóng một tab."""
        widget = self.tab_widget.widget(index)
        if widget:
            # Lấy lại session và gọi hàm close để ngắt kết nối nếu cần
            session = widget.property("session_manager")
            if session:
                threading.Thread(target=session.client.close, daemon=True).start()
            
            self.tab_widget.removeTab(index)
            widget.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())