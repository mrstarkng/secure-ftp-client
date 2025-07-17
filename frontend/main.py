# file: main.py
# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton, QMenu, QSplashScreen, QLabel
from PyQt6.QtGui import QAction, QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from session_manager import SessionManager
from cli_widget import CliWidget
from gui_widget import GuiWidget
from clamav_installer import ensure_clamav_installed, get_clamav_path, update_clamav_database

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure FTP Client")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize ClamAV in background
        self.clamav_ready = False
        self.setup_clamav()

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
    
    def setup_clamav(self):
        """Setup ClamAV in background"""
        # This will be called during startup
        # The actual installation will happen when needed
        self.clamav_ready = True

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
            
            # Shutdown virus scanner if it's a GUI widget
            if hasattr(widget, 'virus_scanner'):
                widget.virus_scanner.shutdown()
            
            self.tab_widget.removeTab(index)
            widget.deleteLater()

    def closeEvent(self, event):
        """Handle application closing"""
        # Shutdown virus scanner for all tabs
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget and hasattr(widget, 'virus_scanner'):
                widget.virus_scanner.shutdown()
        
        # Call parent close event
        super().closeEvent(event)

if __name__ == "__main__":
    # Ensure proper UTF-8 encoding for file paths
    if sys.platform == "win32":
        # Enable UTF-8 mode for Windows
        os.environ["PYTHONIOENCODING"] = "utf-8"
        # Set console encoding to UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Create splash screen
    splash = QSplashScreen()
    splash.setPixmap(QPixmap(400, 300))  # Create a simple colored background
    splash.setStyleSheet("background-color: #2b2b2b; color: white;")
    
    # Add splash screen content
    splash_label = QLabel("Secure FTP Client\n\nInitializing...", splash)
    splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    splash_label.setFont(QFont("Arial", 14))
    splash_label.setStyleSheet("color: white; padding: 20px;")
    splash_label.setGeometry(0, 0, 400, 300)
    
    splash.show()
    app.processEvents()
    
    # Setup ClamAV automatically
    splash_label.setText("Secure FTP Client\n\nSetting up antivirus protection...")
    app.processEvents()
    
    # This will automatically install ClamAV if needed
    clamav_available = ensure_clamav_installed(splash)
    
    if clamav_available:
        # After ensuring it's installed, try to update the database
        splash_label.setText("Secure FTP Client\n\nUpdating virus definitions...")
        app.processEvents()
        
        clamav_path = get_clamav_path()
        if clamav_path:
            def update_status(message):
                splash_label.setText(f"Secure FTP Client\n\n{message}")
                app.processEvents()
            
            success, message = update_clamav_database(clamav_path, update_status)
            if success:
                splash_label.setText("Secure FTP Client\n\nAntivirus protection ready!")
            else:
                splash_label.setText(f"Secure FTP Client\n\nAntivirus installed, but database update failed:\n{message}")
        else:
            splash_label.setText("Secure FTP Client\n\nAntivirus protection ready!")
    else:
        splash_label.setText("Secure FTP Client\n\nStarting without antivirus protection...")
    
    app.processEvents()
    
    # Small delay to show the final message
    QTimer.singleShot(1000, lambda: None)
    for _ in range(10):  # Simple delay loop
        app.processEvents()
        QTimer.singleShot(100, lambda: None)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Hide splash screen
    splash.hide()
    
    sys.exit(app.exec())