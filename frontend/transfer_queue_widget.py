"""
Transfer Queue Widget for FTP Client

This widget displays the status of parallel file transfers with progress bars.
"""

import os
import uuid
from typing import Dict, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QLabel, QPushButton, QGroupBox, QSplitter, QHeaderView,
    QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QAction

from connection_pool import ConnectionPool, TransferJob, TransferType

class TransferQueueWidget(QWidget):
    """Widget to display and manage file transfer queue"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connection_pool: ConnectionPool = None
        self.transfer_items: Dict[str, QTreeWidgetItem] = {}
        self.setup_ui()
        
        # Timer for updating statistics
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Statistics panel
        stats_group = QGroupBox("Transfer Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.stats_label = QLabel("Ready")
        self.stats_label.setStyleSheet("font-family: monospace; font-size: 9px;")
        stats_layout.addWidget(self.stats_label)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.pause_all_btn = QPushButton("Pause All")
        self.pause_all_btn.clicked.connect(self.pause_all_transfers)
        self.pause_all_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_all_btn)
        
        self.resume_all_btn = QPushButton("Resume All")
        self.resume_all_btn.clicked.connect(self.resume_all_transfers)
        self.resume_all_btn.setEnabled(False)
        controls_layout.addWidget(self.resume_all_btn)
        
        self.clear_completed_btn = QPushButton("Clear Completed")
        self.clear_completed_btn.clicked.connect(self.clear_completed_transfers)
        controls_layout.addWidget(self.clear_completed_btn)
        
        controls_layout.addStretch()
        stats_layout.addLayout(controls_layout)
        
        layout.addWidget(stats_group)
        
        # Transfer queue tree
        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderLabels([
            "File", "Type", "Status", "Progress", "Speed", "ETA", "Size"
        ])
        
        # Configure columns
        header = self.queue_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # File name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Progress
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # ETA
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Size
        
        self.queue_tree.setColumnWidth(3, 150)  # Progress column
        
        # Context menu
        self.queue_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.queue_tree)
        
        # Overall progress bar
        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)
        layout.addWidget(self.overall_progress)
        
    def set_connection_pool(self, pool: ConnectionPool):
        """Set the connection pool to monitor"""
        self.connection_pool = pool
        
        # Connect signals
        pool.job_started.connect(self.on_job_started)
        pool.job_progress.connect(self.on_job_progress)
        pool.job_completed.connect(self.on_job_completed)
        pool.connection_state_changed.connect(self.on_connection_state_changed)
        
        # Set up update timer for real-time statistics
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(1000)  # Update every second
        
    def add_transfer_jobs(self, jobs: List[TransferJob]):
        """Add multiple transfer jobs to the queue"""
        for job in jobs:
            self.add_transfer_job(job)
            
    def add_transfer_job(self, job: TransferJob):
        """Add a single transfer job to the display"""
        item = QTreeWidgetItem(self.queue_tree)
        
        # Set basic info
        filename = os.path.basename(job.local_path)
        item.setText(0, filename)
        item.setText(1, "↑" if job.transfer_type == TransferType.UPLOAD else "↓")
        item.setText(2, "Queued")
        item.setText(6, self.format_size(job.size))
        
        # Create progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        self.queue_tree.setItemWidget(item, 3, progress_bar)
        
        # Store references
        self.transfer_items[job.job_id] = item
        item.setData(0, Qt.ItemDataRole.UserRole, job)
        
        # Add to connection pool
        if self.connection_pool:
            self.connection_pool.add_transfer_job(job)
            
    def create_upload_jobs(self, local_paths: List[str], remote_base_path: str = "") -> List[TransferJob]:
        """Create upload jobs for multiple files"""
        jobs = []
        for local_path in local_paths:
            if os.path.exists(local_path):
                filename = os.path.basename(local_path)
                remote_path = f"{remote_base_path}/{filename}" if remote_base_path else filename
                
                job = TransferJob(
                    job_id=str(uuid.uuid4()),
                    transfer_type=TransferType.UPLOAD,
                    local_path=local_path,
                    remote_path=remote_path,
                    size=os.path.getsize(local_path) if os.path.isfile(local_path) else 0
                )
                jobs.append(job)
        return jobs
    
    def create_download_jobs(self, remote_files: List[str], local_base_path: str) -> List[TransferJob]:
        """Create download jobs for multiple files"""
        jobs = []
        for remote_file in remote_files:
            local_path = os.path.join(local_base_path, os.path.basename(remote_file))
            
            job = TransferJob(
                job_id=str(uuid.uuid4()),
                transfer_type=TransferType.DOWNLOAD,
                local_path=local_path,
                remote_path=remote_file,
                size=0  # Size will be determined during transfer
            )
            jobs.append(job)
        return jobs
    
    def add_transfer_jobs(self, jobs: List[TransferJob]):
        """Add multiple transfer jobs to the queue"""
        for job in jobs:
            self.add_transfer_job(job)
    
    def add_transfer_job(self, job: TransferJob):
        """Add a single transfer job to the queue"""
        # Create tree item
        item = QTreeWidgetItem()
        item.setText(0, os.path.basename(job.local_path))
        item.setText(1, "Upload" if job.transfer_type == TransferType.UPLOAD else "Download")
        item.setText(2, "Queued")
        item.setText(4, "Calculating...")  # Speed
        item.setText(5, "Calculating...")  # ETA
        item.setText(6, self.format_size(job.size))  # Size
        item.setData(0, Qt.ItemDataRole.UserRole, job)
        
        # Add to tree
        self.queue_tree.addTopLevelItem(item)
        
        # Create progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setFormat("%p%")  # Show percentage
        progress_bar.setTextVisible(True)
        self.queue_tree.setItemWidget(item, 3, progress_bar)
        
        # Store reference
        self.transfer_items[job.job_id] = item
        
        # Add to connection pool
        self.connection_pool.add_transfer_job(job)
        
        self.update_statistics()
    
    @pyqtSlot(str)
    def on_job_started(self, job_id: str):
        """Handle job started signal"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            item.setText(2, "Transferring")
            
            # Reset progress bar
            progress_bar = self.queue_tree.itemWidget(item, 3)
            if progress_bar:
                progress_bar.setValue(0)
                progress_bar.setStyleSheet("")  # Reset any error styling
            
            # Clear speed initially
            item.setText(4, "Starting...")
            item.setText(5, "Starting...")
            
            self.update_statistics()
            
    @pyqtSlot(str, float)
    def on_job_progress(self, job_id: str, progress: float):
        """Handle job progress signal"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            
            # Update progress bar
            progress_bar = self.queue_tree.itemWidget(item, 3)
            if progress_bar:
                progress_bar.setValue(int(progress))
                
                # Get job data to show detailed progress
                job = item.data(0, Qt.ItemDataRole.UserRole)
                if job and hasattr(job, 'bytes_transferred') and hasattr(job, 'size'):
                    if job.size > 0:
                        transferred_str = self.format_size(job.bytes_transferred)
                        total_str = self.format_size(job.size)
                        progress_bar.setFormat(f"{progress:.1f}% ({transferred_str}/{total_str})")
                    else:
                        progress_bar.setFormat(f"{progress:.1f}%")
                else:
                    progress_bar.setFormat(f"{progress:.1f}%")
            
            # Update speed and ETA columns
            job = item.data(0, Qt.ItemDataRole.UserRole)
            if job and hasattr(job, 'speed') and job.speed > 0:
                speed_text = self.format_speed(job.speed)
                item.setText(4, speed_text)
                
                # Calculate ETA
                if hasattr(job, 'size') and hasattr(job, 'bytes_transferred') and job.size > 0 and job.bytes_transferred > 0:
                    remaining_bytes = job.size - job.bytes_transferred
                    eta_seconds = remaining_bytes / job.speed if job.speed > 0 else 0
                    eta_text = self.format_time(eta_seconds)
                    item.setText(5, eta_text)
                else:
                    item.setText(5, "Calculating...")
            else:
                item.setText(4, "Calculating...")
                item.setText(5, "Calculating...")
            
            # Update overall statistics
            self.update_statistics()
                
    @pyqtSlot(str, bool, str)
    def on_job_completed(self, job_id: str, success: bool, message: str):
        """Handle job completed signal"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            status = "Completed" if success else "Failed"
            item.setText(2, status)
            
            # Update progress bar
            progress_bar = self.queue_tree.itemWidget(item, 3)
            if progress_bar:
                progress_bar.setValue(100 if success else 0)
                if not success:
                    progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
                else:
                    progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")
            
            # Clear speed and ETA for completed transfers
            if success:
                item.setText(4, "Completed")
                item.setText(5, "Done")
            else:
                item.setText(4, "Failed")
                item.setText(5, "Error")
                
            self.update_statistics()
    
    @pyqtSlot(str, str)
    def on_connection_state_changed(self, connection_id: str, state: str):
        """Handle connection state change"""
        # Update UI based on connection state if needed
        pass
    
    def update_statistics(self):
        """Update transfer statistics display"""
        if not self.connection_pool:
            return
            
        stats = self.connection_pool.get_statistics()
        
        # Calculate current transfer speeds from individual jobs
        current_speed = 0
        total_progress = 0
        active_transfers = 0
        
        for job_id, item in self.transfer_items.items():
            job = item.data(0, Qt.ItemDataRole.UserRole)
            if job and hasattr(job, 'speed') and job.speed > 0:
                current_speed += job.speed
                
            # Count active transfers and their progress
            status = item.text(2)
            if status == "Transferring":
                active_transfers += 1
                if job and hasattr(job, 'progress'):
                    total_progress += job.progress
        
        # Calculate average progress for active transfers
        avg_progress = total_progress / active_transfers if active_transfers > 0 else 0
        
        # Format statistics display
        stats_text = (
            f"Connections: {stats['active_connections']}/{stats['total_connections']} idle, "
            f"{stats['busy_connections']} busy | "
            f"Transfers: {stats['active_transfers']} active, "
            f"{stats['completed_transfers']} completed, "
            f"{stats['queued_transfers']} queued | "
            f"Speed: {self.format_speed(current_speed)} | "
            f"Total: {self.format_size(stats['total_bytes_transferred'])}"
        )
        
        self.stats_label.setText(stats_text)
        
        # Update overall progress bar
        total_transfers = stats['active_transfers'] + stats['completed_transfers'] + stats['queued_transfers']
        if total_transfers > 0:
            # Calculate overall completion percentage
            completed_percentage = (stats['completed_transfers'] / total_transfers) * 100
            
            # Add partial progress from active transfers
            if active_transfers > 0:
                partial_progress = (avg_progress / 100) * (active_transfers / total_transfers) * 100
                completed_percentage += partial_progress
            
            self.overall_progress.setValue(int(completed_percentage))
            self.overall_progress.setVisible(True)
            self.overall_progress.setFormat(f"{completed_percentage:.1f}% ({stats['completed_transfers']}/{total_transfers})")
        else:
            self.overall_progress.setVisible(False)
    
    def show_context_menu(self, position):
        """Show context menu for transfer items"""
        item = self.queue_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        # Get job data
        job = item.data(0, Qt.ItemDataRole.UserRole)
        status = item.text(2)
        
        if status == "Queued":
            cancel_action = QAction("Cancel", self)
            cancel_action.triggered.connect(lambda: self.cancel_transfer(job.job_id))
            menu.addAction(cancel_action)
        elif status == "Transferring":
            pause_action = QAction("Pause", self)
            pause_action.triggered.connect(lambda: self.pause_transfer(job.job_id))
            menu.addAction(pause_action)
        elif status == "Failed":
            retry_action = QAction("Retry", self)
            retry_action.triggered.connect(lambda: self.retry_transfer(job.job_id))
            menu.addAction(retry_action)
            
        if status in ["Completed", "Failed"]:
            remove_action = QAction("Remove from list", self)
            remove_action.triggered.connect(lambda: self.remove_transfer(job.job_id))
            menu.addAction(remove_action)
            
        menu.exec(self.queue_tree.mapToGlobal(position))
    
    def cancel_transfer(self, job_id: str):
        """Cancel a queued transfer"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            item.setText(2, "Cancelled")
            # TODO: Remove from connection pool queue
            
    def pause_transfer(self, job_id: str):
        """Pause an active transfer"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            item.setText(2, "Paused")
            # TODO: Implement pause functionality
            
    def retry_transfer(self, job_id: str):
        """Retry a failed transfer"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            job = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Reset progress
            progress_bar = self.queue_tree.itemWidget(item, 3)
            if progress_bar:
                progress_bar.setValue(0)
                progress_bar.setStyleSheet("")  # Reset style
            
            # Re-add to queue
            item.setText(2, "Queued")
            if self.connection_pool:
                self.connection_pool.add_transfer_job(job)
                
    def remove_transfer(self, job_id: str):
        """Remove a transfer from the list"""
        if job_id in self.transfer_items:
            item = self.transfer_items[job_id]
            index = self.queue_tree.indexOfTopLevelItem(item)
            if index >= 0:
                self.queue_tree.takeTopLevelItem(index)
            del self.transfer_items[job_id]
    
    def pause_all_transfers(self):
        """Pause all active transfers"""
        # TODO: Implement pause all functionality
        pass
    
    def resume_all_transfers(self):
        """Resume all paused transfers"""
        # TODO: Implement resume all functionality
        pass
    
    def clear_completed_transfers(self):
        """Clear all completed transfers from the list"""
        items_to_remove = []
        
        for job_id, item in self.transfer_items.items():
            status = item.text(2)
            if status in ["Completed", "Failed", "Cancelled"]:
                items_to_remove.append(job_id)
        
        for job_id in items_to_remove:
            self.remove_transfer(job_id)
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {units[i]}"
    
    def format_speed(self, bytes_per_second: float) -> str:
        """Format transfer speed in human readable format"""
        return f"{self.format_size(int(bytes_per_second))}/s"
    
    def format_time(self, seconds: float) -> str:
        """Format time in human readable format"""
        if seconds <= 0:
            return "Unknown"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
