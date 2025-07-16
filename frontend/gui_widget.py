import sys
import os
import shlex
import re
import urllib.parse
import datetime
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QSplitter,
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QStatusBar,
    QDockWidget, QTextEdit, QLabel, QPushButton, QFormLayout, QFrame,
    QGroupBox, QMessageBox, QCheckBox, QSpinBox, QMenu, QHeaderView,
    QAbstractItemView, QInputDialog, QFileDialog
)
from PyQt6.QtGui import QIcon, QAction, QFileSystemModel, QFont, QStandardItemModel, QStandardItem, QDrag
from PyQt6.QtCore import QDir, Qt, QModelIndex, QTimer, QMimeData

# Import the actual session manager from your project
from session_manager import SessionManager

# --- Custom Widgets ---
class DragDropTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.clipboard_data = None
        self.clipboard_action = None
        self.parent_widget = None
        
    def set_parent_widget(self, parent_widget):
        self.parent_widget = parent_widget
        
    def dragEnterEvent(self, event):
        if (event.mimeData().hasUrls() or 
            event.mimeData().hasFormat("application/x-remote-files")):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        if (event.mimeData().hasUrls() or 
            event.mimeData().hasFormat("application/x-remote-files")):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-remote-files"):
            # Handle remote files dropped to local
            remote_files_data = event.mimeData().data("application/x-remote-files")
            remote_files = remote_files_data.data().decode('utf-8').split('\n')
            
            target_index = self.indexAt(event.position().toPoint())
            if target_index.isValid():
                target_path = self.model().filePath(target_index)
                # If target is a file, use its parent directory
                if not self.model().isDir(target_index):
                    target_path = os.path.dirname(target_path)
            else:
                target_path = self.parent_widget.local_address_bar.text() if self.parent_widget else QDir.currentPath()
            
            # Ensure target directory exists
            if not os.path.exists(target_path):
                try:
                    os.makedirs(target_path, exist_ok=True)
                    print(f"Created directory: {target_path}")
                except Exception as e:
                    print(f"Failed to create directory {target_path}: {e}")
                    return
            
            # Download each remote file
            for remote_file in remote_files:
                if remote_file.strip() and self.parent_widget:
                    self.parent_widget.download_file(remote_file.strip(), target_path)
            
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            # Handle local files as before
            urls = event.mimeData().urls()
            target_index = self.indexAt(event.position().toPoint())
            for url in urls:
                if url.isLocalFile():
                    source_path = url.toLocalFile()
                    if target_index.isValid():
                        target_path = self.model().filePath(target_index)
                        if self.model().isDir(target_index):
                            if self.parent_widget and hasattr(self.parent_widget, 'upload_file'):
                                self.parent_widget.upload_file(source_path, target_path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
        
    def show_context_menu(self, position):
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get unique rows (since we have multiple columns)
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        menu = QMenu(self)
        
        if len(selected_rows) == 1:
            # Single item context menu
            index = self.indexAt(position)
            cut_action = QAction("Cut", self)
            cut_action.triggered.connect(lambda: self.cut_item(index))
            menu.addAction(cut_action)
            
            copy_action = QAction("Copy", self)
            copy_action.triggered.connect(lambda: self.copy_item(index))
            menu.addAction(copy_action)
            
            paste_action = QAction("Paste", self)
            paste_action.setEnabled(self.clipboard_data is not None)
            paste_action.triggered.connect(lambda: self.paste_item(index))
            menu.addAction(paste_action)
            
            menu.addSeparator()
            
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_item(index))
            menu.addAction(delete_action)
        else:
            # Multiple items context menu
            copy_action = QAction(f"Copy {len(selected_rows)} items", self)
            copy_action.triggered.connect(self.copy_multiple_items)
            menu.addAction(copy_action)
            
            delete_action = QAction(f"Delete {len(selected_rows)} items", self)
            delete_action.triggered.connect(self.delete_multiple_items)
            menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(position))
        
    def cut_item(self, index):
        if hasattr(self.model(), 'filePath'):
            self.clipboard_data = self.model().filePath(index)
            self.clipboard_action = 'cut'
            
    def copy_item(self, index):
        if hasattr(self.model(), 'filePath'):
            self.clipboard_data = self.model().filePath(index)
            self.clipboard_action = 'copy'
            
    def paste_item(self, index):
        if self.clipboard_data and hasattr(self.model(), 'filePath'):
            destination = self.model().filePath(index)
            if self.model().isDir(index):
                print(f"Paste {self.clipboard_data} to {destination} ({self.clipboard_action})")
    
    def copy_multiple_items(self):
        selected_indexes = self.selectedIndexes()
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        paths = []
        for row in selected_rows:
            index = self.model().index(row, 0)
            if hasattr(self.model(), 'filePath'):
                paths.append(self.model().filePath(index))
        
        self.clipboard_data = paths
        self.clipboard_action = 'copy'

    def delete_item(self, index):
        """Delete a single local file or directory"""
        if hasattr(self.model(), 'filePath'):
            file_path = self.model().filePath(index)
            file_name = os.path.basename(file_path)
            
            # Ask for confirmation
            if os.path.isdir(file_path):
                result = QMessageBox.question(
                    self, "Delete Directory", 
                    f"Are you sure you want to delete directory '{file_name}' and all its contents?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            else:
                result = QMessageBox.question(
                    self, "Delete File", 
                    f"Are you sure you want to delete file '{file_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            
            if result == QMessageBox.StandardButton.Yes:
                try:
                    if os.path.isdir(file_path):
                        # Delete directory and all its contents
                        shutil.rmtree(file_path)
                        self.parent_widget.status_bar.showMessage(f"Directory '{file_name}' deleted successfully", 3000)
                    else:
                        # Delete file
                        os.remove(file_path)
                        self.parent_widget.status_bar.showMessage(f"File '{file_name}' deleted successfully", 3000)
                    
                    # Refresh the local view
                    if self.parent_widget:
                        self.parent_widget.refresh_local_directory()
                        
                except Exception as e:
                    QMessageBox.critical(
                        self, "Delete Error", 
                        f"Failed to delete '{file_name}': {str(e)}"
                    )
                    self.parent_widget.status_bar.showMessage(f"Failed to delete '{file_name}': {str(e)}", 5000)

    def delete_multiple_items(self):
        """Delete multiple selected local files and directories"""
        selected_indexes = self.selectedIndexes()
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        if not selected_rows:
            return
        
        # Get file paths and names for confirmation
        items_to_delete = []
        for row in selected_rows:
            index = self.model().index(row, 0)
            if hasattr(self.model(), 'filePath'):
                file_path = self.model().filePath(index)
                file_name = os.path.basename(file_path)
                is_dir = os.path.isdir(file_path)
                items_to_delete.append((file_path, file_name, is_dir))
        
        if not items_to_delete:
            return
        
        # Create confirmation message
        file_count = sum(1 for _, _, is_dir in items_to_delete if not is_dir)
        dir_count = sum(1 for _, _, is_dir in items_to_delete if is_dir)
        
        message_parts = []
        if file_count > 0:
            message_parts.append(f"{file_count} file{'s' if file_count > 1 else ''}")
        if dir_count > 0:
            message_parts.append(f"{dir_count} director{'ies' if dir_count > 1 else 'y'}")
        
        message = f"Are you sure you want to delete {' and '.join(message_parts)}?"
        if dir_count > 0:
            message += "\n\nDirectories will be deleted along with all their contents."
        
        result = QMessageBox.question(
            self, "Delete Multiple Items", 
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            success_count = 0
            failed_items = []
            
            for file_path, file_name, is_dir in items_to_delete:
                try:
                    if is_dir:
                        # Delete directory and all its contents
                        shutil.rmtree(file_path)
                    else:
                        # Delete file
                        os.remove(file_path)
                    success_count += 1
                except Exception as e:
                    failed_items.append((file_name, str(e)))
            
            # Show results
            if failed_items:
                error_message = f"Successfully deleted {success_count} items.\n\nFailed to delete:\n"
                for item_name, error in failed_items:
                    error_message += f"• {item_name}: {error}\n"
                QMessageBox.warning(self, "Delete Results", error_message)
                self.parent_widget.status_bar.showMessage(f"Deleted {success_count} items with {len(failed_items)} failures", 5000)
            else:
                self.parent_widget.status_bar.showMessage(f"Successfully deleted {success_count} items", 3000)
            
            # Refresh the local view
            if self.parent_widget:
                self.parent_widget.refresh_local_directory()

class RemoteFileModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(['Name', 'Size', 'Type', 'Date Modified', 'Permissions'])
        self.current_path = "/"  # Keep track of current remote path
        
    def add_file_entry(self, name, size="", file_type="", date_modified="", permissions=""):
        name_item = QStandardItem(name)
        size_item = QStandardItem(size)
        type_item = QStandardItem(file_type)
        date_item = QStandardItem(date_modified)
        perm_item = QStandardItem(permissions)
        
        style = QApplication.style()
        icon = style.standardIcon(style.StandardPixmap.SP_DirIcon if file_type == "Directory" else style.StandardPixmap.SP_FileIcon)
        name_item.setIcon(icon)
        
        # Store the file type as user data for easier access
        name_item.setData(file_type, Qt.ItemDataRole.UserRole)
            
        self.appendRow([name_item, size_item, type_item, date_item, perm_item])

class RemoteTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setHeaderHidden(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.doubleClicked.connect(self.on_item_double_clicked)  # Connect double-click signal
        header = self.header()
        header.setStretchLastSection(False)
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        self.parent_widget = None
        
    def set_parent_widget(self, parent_widget):
        self.parent_widget = parent_widget
        
    def startDrag(self, supportedActions):
        """Start drag operation for remote files"""
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get unique rows
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        # Create drag data
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store remote file paths for download
        remote_paths = []
        for row in selected_rows:
            item = self.model().item(row, 0)
            if item:
                remote_paths.append(item.text())
        
        # Use custom mime type for remote files
        mime_data.setData("application/x-remote-files", 
                         '\n'.join(remote_paths).encode('utf-8'))
        
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag initiation"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if not hasattr(self, 'drag_start_position'):
            return
        
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        self.startDrag(Qt.DropAction.CopyAction)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            target_index = self.indexAt(event.position().toPoint())
            
            # Determine target directory based on where the drop occurred
            if target_index.isValid():
                item = self.model().item(target_index.row(), 0)
                item_type = item.data(Qt.ItemDataRole.UserRole)
                if item_type == "Directory":
                    # Drop onto a directory - use it as target
                    target_dir = item.text()
                    self.parent_widget.change_remote_directory(target_dir)
                    
                    # Upload each file/folder with preserveFolderStructure=True
                    for url in urls:
                        if url.isLocalFile():
                            source_path = url.toLocalFile()
                            if self.parent_widget:
                                self.parent_widget.upload_file(source_path, preserve_structure=True)
                    
                    # Go back to the previous directory
                    self.parent_widget.change_remote_directory("..")
                else:
                    # Drop onto a file or empty space - use current directory
                    for url in urls:
                        if url.isLocalFile():
                            source_path = url.toLocalFile()
                            if self.parent_widget:
                                self.parent_widget.upload_file(source_path, preserve_structure=True)
            else:
                # Drop onto empty space - use current directory
                for url in urls:
                    if url.isLocalFile():
                        source_path = url.toLocalFile()
                        if self.parent_widget:
                            self.parent_widget.upload_file(source_path, preserve_structure=True)
                    
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
    
    def on_item_double_clicked(self, index):
        """Handle double-click on remote items to navigate directories"""
        if self.model() and index.isValid():
            item = self.model().item(index.row(), 0)
            item_type = item.data(Qt.ItemDataRole.UserRole)
            item_name = item.text()
            
            # Navigate to directory on double-click
            if item_type == "Directory":
                if self.parent_widget:
                    self.parent_widget.change_remote_directory(item_name)
            else:
                # Could implement a file preview or download here
                pass
        
    def show_context_menu(self, position):
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get unique rows
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        menu = QMenu(self)
        
        if len(selected_rows) == 1:
            # Single item menu
            index = self.indexAt(position)
            if not index.isValid():
                return
                
            item = self.model().item(index.row(), 0)
            item_type = item.data(Qt.ItemDataRole.UserRole)
            
            if item_type == "Directory":
                open_dir_action = QAction("Open Directory", self)
                open_dir_action.triggered.connect(lambda: self.open_directory(index))
                menu.addAction(open_dir_action)
                menu.addSeparator()
            
            download_action = QAction("Download", self)
            download_action.triggered.connect(lambda: self.download_item(index))
            menu.addAction(download_action)
            
            download_to_action = QAction("Download to...", self)
            download_to_action.triggered.connect(lambda: self.download_item_to(index))
            menu.addAction(download_to_action)
            
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_remote_item(index))
            menu.addAction(delete_action)
            
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self.rename_item(index))
            menu.addAction(rename_action)
        else:
            # Multiple items menu
            download_action = QAction(f"Download {len(selected_rows)} items", self)
            download_action.triggered.connect(self.download_multiple_items)
            menu.addAction(download_action)
            
            download_to_action = QAction(f"Download {len(selected_rows)} items to...", self)
            download_to_action.triggered.connect(self.download_multiple_items_to)
            menu.addAction(download_to_action)
            
            delete_action = QAction(f"Delete {len(selected_rows)} items", self)
            delete_action.triggered.connect(self.delete_multiple_items)
            menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def open_directory(self, index):
        """Opens the directory at the given index"""
        if self.model():
            item_name = self.model().item(index.row(), 0).text()
            if self.parent_widget:
                self.parent_widget.change_remote_directory(item_name)
        
    def download_item(self, index):
        if self.model():
            item_name = self.model().item(index.row(), 0).text()
            if self.parent_widget and hasattr(self.parent_widget, 'download_file'):
                current_local_dir = self.parent_widget.local_address_bar.text()
                self.parent_widget.download_file(item_name, current_local_dir)

    def download_item_to(self, index):
        """Download item to a user-selected location"""
        if self.model():
            item_name = self.model().item(index.row(), 0).text()
            if self.parent_widget and hasattr(self.parent_widget, 'download_file'):
                # Let user choose download location
                download_dir = QFileDialog.getExistingDirectory(
                    self, 
                    f"Select download location for {item_name}",
                    self.parent_widget.local_address_bar.text()
                )
                if download_dir:
                    self.parent_widget.download_file(item_name, download_dir)

    def download_multiple_items(self):
        """Download multiple selected items"""
        selected_indexes = self.selectedIndexes()
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        # Get the current local directory for downloads
        current_local_dir = self.parent_widget.local_address_bar.text() if self.parent_widget else QDir.currentPath()
        
        for row in selected_rows:
            item = self.model().item(row, 0)
            if item and self.parent_widget:
                remote_filename = item.text()
                # Skip the ".." entry
                if remote_filename != "..":
                    self.parent_widget.download_file(remote_filename, current_local_dir)

    def download_multiple_items_to(self):
        """Download multiple items to a user-selected location"""
        selected_indexes = self.selectedIndexes()
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        if not selected_rows:
            return
        
        # Let user choose download location
        download_dir = QFileDialog.getExistingDirectory(
            self, 
            f"Select download location for {len(selected_rows)} items",
            self.parent_widget.local_address_bar.text() if self.parent_widget else QDir.currentPath()
        )
        
        if download_dir:
            for row in selected_rows:
                item = self.model().item(row, 0)
                if item and self.parent_widget:
                    remote_filename = item.text()
                    # Skip the ".." entry
                    if remote_filename != "..":
                        self.parent_widget.download_file(remote_filename, download_dir)

    def delete_multiple_items(self):
        """Delete multiple selected items"""
        selected_indexes = self.selectedIndexes()
        selected_rows = list(set(index.row() for index in selected_indexes))
        
        if QMessageBox.question(self, "Delete Multiple Items", 
                              f"Are you sure you want to delete {len(selected_rows)} items?",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            
            for row in selected_rows:
                item = self.model().item(row, 0)
                if item and self.parent_widget:
                    item_name = item.text()
                    # Skip the ".." entry
                    if item_name != "..":
                        item_type = item.data(Qt.ItemDataRole.UserRole)
                        if item_type == "Directory":
                            self.parent_widget.execute_command(f"rmdir {shlex.quote(item_name)}")
                        else:
                            self.parent_widget.execute_command(f"delete {shlex.quote(item_name)}")
            
    def delete_remote_item(self, index):
        if self.model():
            item_name = self.model().item(index.row(), 0).text()
            item_type = self.model().item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
            
            if self.parent_widget:
                if item_type == "Directory":
                    # Ask for confirmation before deleting a directory
                    result = QMessageBox.question(
                        self, "Delete Directory", 
                        f"Do you want to delete directory '{item_name}' and all its contents?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if result == QMessageBox.StandardButton.Yes:
                        # This command will now trigger the recursive rmdir implementation in the C++ backend
                        self.parent_widget.execute_command(f"rmdir {shlex.quote(item_name)}")
                else:
                    self.parent_widget.execute_command(f"delete {shlex.quote(item_name)}")
            
    def rename_item(self, index):
        if self.model():
            item_name = self.model().item(index.row(), 0).text()
            new_name, ok = QInputDialog.getText(
                self, "Rename Item", 
                "Enter new name:", 
                text=item_name
            )
            if ok and new_name and new_name != item_name:
                if self.parent_widget:
                    self.parent_widget.execute_command(f"rename {shlex.quote(item_name)} {shlex.quote(new_name)}")

# --- Main Application Window ---
class GuiWidget(QMainWindow):
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session = session_manager
        self.setWindowTitle("Secure FTP Client")
        self.setGeometry(100, 100, 1300, 800)
        self.setWindowIcon(QIcon.fromTheme("network-server"))
        
        # Track current remote directory
        self.current_remote_dir = "/"
        
        # Buffer for output to prevent misinterpretation
        self.ls_output_buffer = ""
        self.expecting_ls_output = False
        self.last_command = ""
        self.last_cd_target = ""  # Keep track of the last CD target
        self.just_connected = False  # Flag to indicate that we just connected

        # --- Models ---
        self.local_model = QFileSystemModel()
        self.local_model.setRootPath(QDir.currentPath())
        self.remote_model = RemoteFileModel(self)

        # --- UI Components ---
        self.setup_central_widget()
        self.create_connection_panel()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Enter connection details or paste a full FTP URL.")

        # --- Signal/Slot Connections ---
        self.setup_connections()
        
        # Timer for updating the timestamp
        self.timestamp_timer = QTimer(self)
        self.timestamp_timer.timeout.connect(self.update_timestamp)
        self.timestamp_timer.start(60000)  # Update every minute
        self.update_timestamp()  # Initial update

    def setup_central_widget(self):
        # Left panel for local files
        local_panel = QWidget()
        local_layout = QVBoxLayout(local_panel)
        local_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add local navigation bar with up button
        local_address_layout = QHBoxLayout()
        
        # Add up directory button for local
        self.local_up_dir_button = QPushButton()
        self.local_up_dir_button.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowUp))
        self.local_up_dir_button.setToolTip("Go up one directory")
        self.local_up_dir_button.clicked.connect(self.go_up_local_directory)
        local_address_layout.addWidget(self.local_up_dir_button)
        
        # Local address bar
        self.local_address_bar = QLineEdit(QDir.currentPath())
        self.local_address_bar.setPlaceholderText("Local directory path")
        local_address_layout.addWidget(self.local_address_bar)
        
        # Add refresh button for local
        self.local_refresh_button = QPushButton()
        self.local_refresh_button.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_BrowserReload))
        self.local_refresh_button.setToolTip("Refresh local directory")
        self.local_refresh_button.clicked.connect(self.refresh_local_directory)
        local_address_layout.addWidget(self.local_refresh_button)
        
        local_layout.addLayout(local_address_layout)
        
        # Local tree view
        self.local_tree = DragDropTreeView()
        self.local_tree.setModel(self.local_model)
        self.local_tree.setRootIndex(self.local_model.index(QDir.currentPath()))
        self.local_tree.setHeaderHidden(False)
        self.local_tree.setSortingEnabled(True)
        self.local_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        header = self.local_tree.header()
        header.setStretchLastSection(False)
        for i in range(4): header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        self.local_tree.setColumnWidth(0, 250)
        self.local_tree.setColumnWidth(1, 100)
        self.local_tree.setColumnWidth(2, 100)
        self.local_tree.setColumnWidth(3, 150)
        local_layout.addWidget(self.local_tree)
        
        # Right panel for remote files
        remote_panel = QWidget()
        remote_layout = QVBoxLayout(remote_panel)
        remote_layout.setContentsMargins(0, 0, 0, 0)
        
        # Remote address/navigation bar with navigation buttons
        remote_address_layout = QHBoxLayout()
        
        # Add up directory button
        self.up_dir_button = QPushButton()
        self.up_dir_button.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowUp))
        self.up_dir_button.setToolTip("Go up one directory")
        self.up_dir_button.clicked.connect(lambda: self.change_remote_directory(".."))
        self.up_dir_button.setEnabled(False)  # Disabled until connected
        remote_address_layout.addWidget(self.up_dir_button)
        
        # Remote address bar
        self.remote_address_bar = QLineEdit()
        self.remote_address_bar.setPlaceholderText("Enter FTP URL (ftp://user:pass@host:port/path) or browse directory")
        remote_address_layout.addWidget(self.remote_address_bar)
        
        # Add refresh button
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh current directory")
        self.refresh_button.clicked.connect(self.refresh_remote_directory)
        self.refresh_button.setEnabled(False)  # Disabled until connected
        remote_address_layout.addWidget(self.refresh_button)
        
        remote_layout.addLayout(remote_address_layout)
        
        # Remote tree view
        self.remote_list = RemoteTreeView()
        self.remote_list.setModel(self.remote_model)
        self.remote_list.setToolTip("Remote files will be displayed here after connecting.")
        self.remote_list.setColumnWidth(0, 200)
        self.remote_list.setColumnWidth(1, 80)
        self.remote_list.setColumnWidth(2, 80)
        self.remote_list.setColumnWidth(3, 130)
        self.remote_list.setColumnWidth(4, 100)
        remote_layout.addWidget(self.remote_list)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(local_panel)
        splitter.addWidget(remote_panel)
        splitter.setSizes([600, 700])
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.addWidget(splitter)
        self.setCentralWidget(main_widget)

    def create_connection_panel(self):
        dock_widget = QDockWidget("Connection & Server Info", self)
        dock_widget.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        dock_widget.setMinimumWidth(350)
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        
        advanced_group = QGroupBox("Advanced Connection")
        advanced_layout = QFormLayout(advanced_group)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("ftp.example.com")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("username")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("password")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(21)
        self.passive_mode = QCheckBox("Passive Mode")
        self.passive_mode.setChecked(True)
        advanced_layout.addRow("Host:", self.host_input)
        advanced_layout.addRow("Username:", self.user_input)
        advanced_layout.addRow("Password:", self.pass_input)
        advanced_layout.addRow("Port:", self.port_input)
        advanced_layout.addRow("", self.passive_mode)
        self.connect_button = QPushButton("Connect")
        advanced_layout.addRow("", self.connect_button)
        main_layout.addWidget(advanced_group)

        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(status_group)
        
        # Connection status label and close button layout
        status_header_layout = QHBoxLayout()
        self.connection_status = QLabel("Not connected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        status_header_layout.addWidget(self.connection_status)
        
        # Add a close connection button directly in the status header
        self.close_connection_button = QPushButton("Close")
        self.close_connection_button.setToolTip("Close the current connection")
        self.close_connection_button.setEnabled(False)
        self.close_connection_button.clicked.connect(self.on_disconnect_clicked)
        status_header_layout.addWidget(self.close_connection_button)
        
        status_layout.addLayout(status_header_layout)
        
        # Original button row
        button_layout = QHBoxLayout()
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.status_button = QPushButton("Status")
        button_layout.addWidget(self.disconnect_button)
        button_layout.addWidget(self.status_button)
        status_layout.addLayout(button_layout)
        
        main_layout.addWidget(status_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        log_group = QGroupBox("Server Communication Log")
        log_layout = QVBoxLayout(log_group)
        self.server_log = QTextEdit()
        self.server_log.setReadOnly(True)
        self.server_log.setMaximumHeight(200)
        self.server_log.setFont(QFont("Consolas", 9))
        self.server_log.setText("Ready. Enter connection details above.")
        log_button_layout = QHBoxLayout()
        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.server_log.clear)
        log_button_layout.addWidget(clear_log_button)
        log_button_layout.addStretch()
        log_layout.addWidget(self.server_log)
        log_layout.addLayout(log_button_layout)
        main_layout.addWidget(log_group)

        # Add current timestamp and user info at the bottom
        self.timestamp_layout = QHBoxLayout()
        self.timestamp_label = QLabel("Last Update: 2025-07-16 14:43:21 UTC | User: Kostovite")
        self.timestamp_label.setStyleSheet("color: gray; font-size: 10px;")
        self.timestamp_layout.addWidget(self.timestamp_label)
        main_layout.addLayout(self.timestamp_layout)

        dock_widget.setWidget(container_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

    def update_timestamp(self):
        """Update the timestamp in the status panel"""
        current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.setText(f"Last Update: {current_time} UTC | User: Kostovite")

    def go_up_local_directory(self):
        """Navigate up one directory in local view"""
        current_path = self.local_address_bar.text()
        parent_path = os.path.dirname(current_path)
        
        if parent_path and parent_path != current_path:
            self.local_address_bar.setText(parent_path)
            self.on_local_address_entered()

    def refresh_local_directory(self):
        """Refresh the local directory view"""
        current_path = self.local_address_bar.text()
        if QDir(current_path).exists():
            self.local_tree.setRootIndex(self.local_model.index(current_path))
            self.status_bar.showMessage("Local directory refreshed", 2000)

    def setup_connections(self):
        self.local_tree.clicked.connect(self.on_local_directory_selected)
        self.local_address_bar.returnPressed.connect(self.on_local_address_entered)
        self.remote_address_bar.returnPressed.connect(self.on_remote_address_entered)
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.status_button.clicked.connect(self.on_status_clicked)
        self.session.output_received.connect(self.handle_server_output)
        self.session.task_finished.connect(self.on_task_finished)
        self.local_tree.set_parent_widget(self)
        self.remote_list.set_parent_widget(self)

    def execute_command(self, command: str):
        """Puts a command on the session manager's queue. This is thread-safe."""
        self.status_bar.showMessage(f"Queueing: {command.split()[0]}...")
        display_command = command
        if command.startswith("open") and len(command.split()) >= 4:
            parts = command.split()
            display_command = f"open {parts[1]} {parts[2]} ****"
        
        # Store the command type for later reference
        command_parts = command.split()
        self.last_command = command_parts[0] if command_parts else command
        
        # Store the target directory if it's a CD command
        if self.last_command == "cd" and len(command_parts) > 1:
            self.last_cd_target = command_parts[1].strip('"\'')
        
        # Prepare for ls output if that's the command
        if self.last_command == "ls":
            self.expecting_ls_output = True
            self.ls_output_buffer = ""
        else:
            self.expecting_ls_output = False
        
        self.server_log.append(f">>> {display_command}")
        self.session.process_command_line(command)

    def refresh_remote_directory(self):
        """Refreshes the current remote directory listing"""
        if self.connection_status.text().startswith("Connected"):
            self.execute_command("ls")
            self.status_bar.showMessage("Refreshing directory listing...", 2000)

    def on_connect_clicked(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        password = self.pass_input.text()
        if not host or not user:
            QMessageBox.warning(self, "Connection Error", "Host and Username are required.")
            return
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(False)
        self.close_connection_button.setEnabled(False)
        # Reset current directory on new connection
        self.current_remote_dir = "/"
        self.just_connected = True  # Set flag to indicate we just connected
        self.execute_command(f"open {host} {user} {password}")

    def on_disconnect_clicked(self):
        self.execute_command("close")
        # Reset UI elements
        self.up_dir_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.remote_address_bar.setText("")
        self.disconnect_button.setEnabled(False)
        self.close_connection_button.setEnabled(False)

    def on_status_clicked(self):
        self.execute_command("status")

    def handle_server_output(self, text: str):
        """Handles output from the server, carefully determining what kind of output it is"""
        self.server_log.append(text)
        
        # Store the output for ls command to be processed in on_task_finished
        if self.expecting_ls_output:
            # Only buffer output that looks like an ls listing
            if text.strip().startswith(('d', '-', 'l')) or '226 Transfer complete' in text:
                self.ls_output_buffer += text + "\n"
        
        # Update connection status based on certain keywords
        if "Successfully connected" in text or "Login successful" in text:
            self.connection_status.setText(f"Connected to {self.host_input.text()}")
            self.connection_status.setStyleSheet("color: green; font-weight: bold;")
            self.status_bar.showMessage("Connected successfully! Listing files...", 4000)
            self.up_dir_button.setEnabled(False)  # Can't go up from root until we confirm path
            self.refresh_button.setEnabled(True)
            self.disconnect_button.setEnabled(True)
            self.close_connection_button.setEnabled(True)
            
            # After connection, we want to get current directory and then list files
            self.execute_command("pwd")
            
        elif "Connection closed" in text or "Goodbye" in text:
            self.connection_status.setText("Not connected")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            self.remote_model.clear()
            self.current_remote_dir = "/"
            self.remote_address_bar.setText("")
            self.up_dir_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.disconnect_button.setEnabled(False)
            self.close_connection_button.setEnabled(False)
            self.just_connected = False
            
        elif "Error" in text or "Failed" in text:
            self.connection_status.setText("Connection failed")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            self.just_connected = False
            
        # Detect PWD responses to update current directory
        elif "257 \"" in text and "\" is the current directory" in text:
            # Extract the path from: 257 "/path/to/dir" is the current directory
            match = re.search(r'257 "([^"]+)"', text)
            if match:
                self.current_remote_dir = match.group(1)
                self.remote_address_bar.setText(self.current_remote_dir)
                self.up_dir_button.setEnabled(self.current_remote_dir != "/")
                
                # If we just connected, immediately refresh the directory listing
                if self.just_connected:
                    self.just_connected = False
                    QTimer.singleShot(100, self.refresh_remote_directory)
                
        # Handle directory change confirmation
        elif "250 Directory successfully changed" in text:
            # If we're responding to a CD command, update directory tracking
            if self.last_command == "cd":
                # Handle special cases
                if self.last_cd_target == "..":
                    # Going up one level
                    if self.current_remote_dir != "/":
                        parent = os.path.dirname(self.current_remote_dir)
                        if not parent:
                            parent = "/"
                        self.current_remote_dir = parent
                elif self.last_cd_target.startswith("/"):
                    # Absolute path
                    self.current_remote_dir = self.last_cd_target
                else:
                    # Relative path - concatenate with current path
                    if self.current_remote_dir.endswith("/"):
                        self.current_remote_dir += self.last_cd_target
                    else:
                        self.current_remote_dir += "/" + self.last_cd_target
                
                # Update UI
                self.remote_address_bar.setText(self.current_remote_dir)
                self.up_dir_button.setEnabled(self.current_remote_dir != "/")
                
                # Refresh directory listing
                self.execute_command("ls")

    def on_task_finished(self, success: bool, command_name: str):
        """Handle completion of commands, particularly 'ls' command"""
        self.connect_button.setEnabled(True)
        if self.connection_status.text().startswith("Connected"):
            self.disconnect_button.setEnabled(True)
            self.close_connection_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
        
        # Process specific commands
        if success:
            if command_name == "ls" and self.expecting_ls_output:
                self.parse_and_display_ls(self.ls_output_buffer)
                self.expecting_ls_output = False
                self.ls_output_buffer = ""
                
            elif command_name == "cd":
                # We already updated the path in handle_server_output
                # Now get a fresh directory listing
                self.execute_command("ls")
                
            elif command_name in ["put", "mput", "mkdir", "rmdir", "delete", "rename"]:
                self.status_bar.showMessage(f"'{command_name}' finished. Refreshing file list...", 3000)
                self.execute_command("ls")
                
            elif command_name == "get":
                self.status_bar.showMessage("Download completed successfully!", 3000)
                # Refresh local directory to show the downloaded file
                self.refresh_local_directory()
        else:
            if command_name == "get":
                self.status_bar.showMessage("Download failed. Check the log for details.", 5000)

    def parse_and_display_ls(self, ls_output: str):
        """Parse ls output to display files, being careful to ignore status messages"""
        self.remote_model.clear()
        self.remote_model.setHorizontalHeaderLabels(['Name', 'Size', 'Type', 'Date Modified', 'Permissions'])
        
        # Add parent directory entry (..) if not at root
        if self.current_remote_dir != "/":
            self.remote_model.add_file_entry(
                name="..",
                size="",
                file_type="Directory",
                date_modified="",
                permissions="d---------"
            )
        
        # Process each line that looks like a file listing
        lines = ls_output.strip().split('\n')
        for line in lines:
            line = line.strip('\r')
            # Skip empty lines, totals, and FTP status codes
            if (not line or 
                line.startswith('total') or 
                re.match(r'^\d{3}', line) or  # FTP reply codes start with 3 digits
                "bytes transferred" in line.lower()):
                continue
            
            # Try to parse as standard Unix ls -l format
            parts = line.split(maxsplit=8)
            if len(parts) >= 9:
                permissions, _, _, _, size, month, day, time_or_year, name = parts
                is_dir = permissions.startswith('d')
                self.remote_model.add_file_entry(
                    name=name, size=size if not is_dir else "",
                    file_type="Directory" if is_dir else "File",
                    date_modified=f"{month} {day} {time_or_year}", permissions=permissions
                )
            elif len(parts) > 0:
                # Couldn't parse in standard format, just use the line as name
                # This is typically for weird file listings or for status messages
                # We'll skip it if it looks like a status message
                if not re.match(r'^\d{3}', parts[0]):  # Not a FTP status code
                    self.remote_model.add_file_entry(name=line)
                
        self.status_bar.showMessage("Remote file list updated.", 2000)

    def upload_file(self, local_path, remote_path=None, preserve_structure=False):
        """
        Uploads a file or directory to the remote server.
        
        Args:
            local_path: Path to the local file or directory
            remote_path: Optional target path on the remote server
            preserve_structure: If True, creates necessary directory structure on server
        """
        is_directory = os.path.isdir(local_path)
        
        # Extract the filename/dirname from the path, discarding absolute path
        basename = os.path.basename(local_path)
        
        # If we want to preserve the folder structure (when dropping directly)
        if preserve_structure and is_directory:
            # Create the directory on the server using just the basename
            self.execute_command(f"mkdir {shlex.quote(basename)}")
            
            # Change into that directory
            self.execute_command(f"cd {shlex.quote(basename)}")
            
            # Upload the contents using mput
            self.execute_command(f"mput {shlex.quote(local_path)}")
            
            # Go back to the parent directory
            self.execute_command("cd ..")
        else:
            # Standard upload without preserving structure
            if is_directory:
                # For directories, we need to create the directory first
                self.execute_command(f"mkdir {shlex.quote(basename)}")
                
                # Then upload the contents
                self.execute_command(f"mput {shlex.quote(local_path)}")
            else:
                # For files, just use put with the source path and optional target name
                if remote_path:
                    self.execute_command(f"put {shlex.quote(local_path)} {shlex.quote(remote_path)}")
                else:
                    # Use just the basename for the target to avoid path issues
                    self.execute_command(f"put {shlex.quote(local_path)} {shlex.quote(basename)}")

    def download_file(self, remote_filename, local_path=None):
        """Download a file from remote to local with proper path handling and debugging"""
        if not remote_filename:
            self.status_bar.showMessage("No remote filename provided", 3000)
            return
        
        # Determine the local file path
        if local_path:
            # If local_path is a directory, append the remote filename
            if os.path.isdir(local_path):
                local_file_path = os.path.join(local_path, remote_filename)
            else:
                # If it's a file path, use it as is
                local_file_path = local_path
        else:
            # Use current local directory with remote filename
            current_local_dir = self.local_address_bar.text()
            local_file_path = os.path.join(current_local_dir, remote_filename)
        
        # Ensure the directory exists
        directory = os.path.dirname(local_file_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"Created directory: {directory}")
                self.server_log.append(f"Created directory: {directory}")
            except Exception as e:
                self.status_bar.showMessage(f"Failed to create directory: {e}", 5000)
                self.server_log.append(f"ERROR: Failed to create directory {directory}: {e}")
                return
        
        # Convert to forward slashes for consistency (Windows handles both)
        local_file_path = local_file_path.replace('\\', '/')
        
        # Log the download attempt
        self.server_log.append(f"DEBUG: Downloading '{remote_filename}' to '{local_file_path}'")
        print(f"DEBUG: Downloading '{remote_filename}' to '{local_file_path}'")
        
        # Check if target file already exists
        if os.path.exists(local_file_path):
            self.server_log.append(f"DEBUG: Target file already exists: {local_file_path}")
            print(f"DEBUG: Target file already exists: {local_file_path}")
        
        command = f"get {shlex.quote(remote_filename)} {shlex.quote(local_file_path)}"
        self.execute_command(command)
        
        self.status_bar.showMessage(f"Downloading {remote_filename} to {local_file_path}...", 3000)

    def on_local_directory_selected(self, index):
        path = self.local_model.filePath(index)
        if self.local_model.isDir(index):
            self.local_address_bar.setText(path)

    def on_local_address_entered(self):
        path = self.local_address_bar.text()
        if QDir(path).exists():
            self.local_tree.setRootIndex(self.local_model.index(path))
        else:
            self.status_bar.showMessage("Local path not found.", 3000)

    def on_remote_address_entered(self):
        url_text = self.remote_address_bar.text().strip()
        if not url_text: return
        if url_text.startswith('ftp://'):
            self.parse_and_connect_ftp_url(url_text)
        else:
            self.change_remote_directory(url_text)

    def change_remote_directory(self, path):
        """Change the remote directory and update UI accordingly"""
        if not path: return
        
        # Execute the cd command
        self.execute_command(f"cd {shlex.quote(path)}")

    def parse_and_connect_ftp_url(self, url_text):
        try:
            parsed = urllib.parse.urlparse(url_text)
            if parsed.scheme != 'ftp':
                QMessageBox.warning(self, "Invalid URL", "Only FTP URLs are supported.")
                return
            host, port = parsed.hostname or "", parsed.port or 21
            user, password = parsed.username or "", parsed.password or ""
            path = parsed.path or "/"
            
            self.host_input.setText(host)
            self.user_input.setText(user)
            self.pass_input.setText(password)
            self.port_input.setValue(port)
            
            self.on_connect_clicked()
            
            if path and path != "/":
                self.execute_command(f"cd {shlex.quote(path)}")
        except Exception as e:
            QMessageBox.warning(self, "URL Parse Error", f"Failed to parse FTP URL: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    session = SessionManager()
    session.start_worker()
    
    main_window = GuiWidget(session_manager=session)
    main_window.show()
    
    app.aboutToQuit.connect(session.stop)
    sys.exit(app.exec())