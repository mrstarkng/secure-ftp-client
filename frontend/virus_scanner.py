# -*- coding: utf-8 -*-
"""
Threaded virus scanner for non-blocking file scanning
"""
import threading
import queue
import time
from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class ScanJob:
    """Represents a single virus scan job"""
    def __init__(self, job_id: str, file_path: str, callback: Callable[[str, str, str], None]):
        self.job_id = job_id
        self.file_path = file_path
        self.callback = callback
        self.created_at = time.time()


class VirusScannerPool(QObject):
    """Thread pool for virus scanning operations"""
    
    # Signals
    scan_completed = pyqtSignal(str, str, str)  # job_id, file_path, result
    
    def __init__(self, max_threads: int = 3):
        super().__init__()
        self.max_threads = max_threads
        self.active_threads = 0
        self.job_queue = queue.Queue()
        self.running = True
        self.lock = threading.Lock()
        
        # Connect signal to handle results on main thread
        self.scan_completed.connect(self._handle_scan_result)
        
        # Start worker threads
        for i in range(max_threads):
            thread = threading.Thread(target=self._worker_thread, daemon=True)
            thread.start()
    
    def scan_file_async(self, job_id: str, file_path: str, callback: Callable[[str, str, str], None]):
        """
        Queue a file for virus scanning
        
        Args:
            job_id: Unique identifier for this scan job
            file_path: Path to the file to scan
            callback: Function to call with results (job_id, file_path, result)
        """
        job = ScanJob(job_id, file_path, callback)
        self.job_queue.put(job)
    
    def _worker_thread(self):
        """Worker thread that processes scan jobs"""
        # Import here to avoid circular imports
        from session_manager import SessionManager
        
        # Create a local client instance for this thread
        # Each thread needs its own client to avoid threading issues
        temp_session = SessionManager()
        
        while self.running:
            try:
                # Get job from queue with timeout
                job = self.job_queue.get(timeout=1.0)
                
                with self.lock:
                    self.active_threads += 1
                
                try:
                    # Perform the actual virus scan
                    result = temp_session.client.scanFile(job.file_path)
                    
                    # Emit signal to main thread
                    self.scan_completed.emit(job.job_id, job.file_path, result)
                    
                except Exception as e:
                    # Handle scan errors
                    error_result = f"ERROR: Failed to scan file: {str(e)}"
                    self.scan_completed.emit(job.job_id, job.file_path, error_result)
                
                finally:
                    with self.lock:
                        self.active_threads -= 1
                    self.job_queue.task_done()
                    
            except queue.Empty:
                # Timeout - continue loop
                continue
            except Exception as e:
                print(f"Error in virus scanner worker thread: {e}")
    
    def _handle_scan_result(self, job_id: str, file_path: str, result: str):
        """Handle scan results on the main thread"""
        # This runs on the main thread due to Qt signal/slot mechanism
        # We need to find and call the appropriate callback
        # Since we can't store callbacks in signals, we'll use a different approach
        pass
    
    def get_queue_size(self) -> int:
        """Get the number of pending scan jobs"""
        return self.job_queue.qsize()
    
    def get_active_threads(self) -> int:
        """Get the number of currently active scan threads"""
        with self.lock:
            return self.active_threads
    
    def shutdown(self):
        """Shutdown the scanner pool"""
        self.running = False


class AsyncVirusScanner(QObject):
    """
    Async virus scanner that provides non-blocking file scanning
    """
    
    # Signals
    scan_completed = pyqtSignal(str, str, str)  # file_path, result, job_id
    scan_failed = pyqtSignal(str, str)  # file_path, reason
    
    def __init__(self, max_concurrent_scans: int = 3):
        super().__init__()
        self.pool = VirusScannerPool(max_concurrent_scans)
        self.pending_jobs = {}  # job_id -> callback mapping
        
        # Connect pool signals
        self.pool.scan_completed.connect(self._on_scan_completed)
    
    def scan_file_async(self, file_path: str, callback: Optional[Callable[[str, str], None]] = None) -> str:
        """
        Scan a file asynchronously
        
        Args:
            file_path: Path to the file to scan
            callback: Optional callback function (file_path, result) -> None
            
        Returns:
            job_id: Unique identifier for this scan job
        """
        import uuid
        job_id = str(uuid.uuid4())
        
        # Store callback for later use
        if callback:
            self.pending_jobs[job_id] = callback
        
        # Queue the scan job
        self.pool.scan_file_async(job_id, file_path, None)  # We handle callbacks ourselves
        
        return job_id
    
    def _on_scan_completed(self, job_id: str, file_path: str, result: str):
        """Handle completed scan results"""
        # Emit signal for UI updates
        self.scan_completed.emit(file_path, result, job_id)
        
        # Call stored callback if any
        if job_id in self.pending_jobs:
            callback = self.pending_jobs.pop(job_id)
            try:
                callback(file_path, result)
            except Exception as e:
                print(f"Error in scan callback: {e}")
        
        # Check if scan failed and emit appropriate signal
        if result.startswith("ERROR:") or result.startswith("INFECTED:"):
            if result.startswith("INFECTED:"):
                virus_name = result.split(":", 1)[1].strip()
                reason = f"File is infected with: {virus_name}. Upload cancelled."
            else:
                reason = f"Antivirus scan failed: {result}. Upload cancelled for safety."
            
            self.scan_failed.emit(file_path, reason)
    
    def get_stats(self) -> dict:
        """Get current scanner statistics"""
        return {
            'queue_size': self.pool.get_queue_size(),
            'active_threads': self.pool.get_active_threads(),
            'max_threads': self.pool.max_threads
        }
    
    def shutdown(self):
        """Shutdown the async scanner"""
        self.pool.shutdown()


# Global instance
_global_scanner = None

def get_virus_scanner(max_concurrent_scans: int = 3) -> AsyncVirusScanner:
    """Get the global virus scanner instance"""
    global _global_scanner
    if _global_scanner is None:
        _global_scanner = AsyncVirusScanner(max_concurrent_scans)
    return _global_scanner
