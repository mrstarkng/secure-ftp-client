# file: main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from session_manager import SessionManager
from cli_widget import CliWidget
from gui_widget import GuiWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure FTP Client")
        self.setGeometry(100, 100, 1400, 900)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        self.tab_widget.setStyleSheet("QTabBar::tab { min-width: 120px; }")
        self.setCentralWidget(self.tab_widget)

        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setFixedSize(24, 24)
        self.tab_widget.setCornerWidget(self.add_tab_button, Qt.Corner.TopLeftCorner)
        
        menu = QMenu(self)
        new_cli_action = QAction("New CLI Session", self)
        new_gui_action = QAction("New GUI Session", self)
        menu.addAction(new_cli_action)
        menu.addAction(new_gui_action)
        self.add_tab_button.setMenu(menu)

        new_cli_action.triggered.connect(self.add_cli_tab)
        new_gui_action.triggered.connect(self.add_gui_tab)

        self.add_gui_tab() # Default to GUI mode

    def add_cli_tab(self):
        session = SessionManager()
        cli_widget = CliWidget(session)
        cli_widget.setProperty("session_manager", session)
        session.start_worker() # Start the worker thread for this session
        
        index = self.tab_widget.addTab(cli_widget, "CLI Session")
        self.tab_widget.setCurrentIndex(index)

    def add_gui_tab(self):
        session = SessionManager()
        gui_widget = GuiWidget(session)
        gui_widget.setProperty("session_manager", session)
        session.start_worker() # Start the worker thread for this session
        
        index = self.tab_widget.addTab(gui_widget, "GUI Session")
        self.tab_widget.setCurrentIndex(index)

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget:
            session = widget.property("session_manager")
            if session:
                session.stop() # Gracefully stop the worker and close connection
            
            self.tab_widget.removeTab(index)
            widget.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())