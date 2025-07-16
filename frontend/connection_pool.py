"""
Connection Pool Manager for Parallel FTP Transfers

This module manages a pool of FTP connections to enable parallel file transfers.
"""

import os
import threading
import queue
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import ftp_engine
except ImportError:
    # Fallback for testing without the C++ module
    ftp_engine = None

class ConnectionState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    CONNECTING = "connecting"
    ERROR = "error"
    DISCONNECTED = "disconnected"

class TransferType(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"

@dataclass
class TransferJob:
    """Represents a single file transfer job"""
    job_id: str
    transfer_type: TransferType
    local_path: str
    remote_path: str
    size: int = 0
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    speed: float = 0.0  # bytes per second
    bytes_transferred: int = 0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = time.time()

@dataclass
class ConnectionInfo:
    """Information about a single FTP connection"""
    connection_id: str
    client: Any  # ftp_engine.FtpClient
    state: ConnectionState
    current_job: Optional[TransferJob] = None
    last_used: float = field(default_factory=time.time)
    error_count: int = 0
    thread: Optional[threading.Thread] = None

class ConnectionPool(QObject):
    """Manages a pool of FTP connections for parallel transfers"""
    
    # Signals for GUI updates
    job_started = pyqtSignal(str)  # job_id
    job_progress = pyqtSignal(str, float)  # job_id, progress
    job_completed = pyqtSignal(str, bool, str)  # job_id, success, message
    connection_state_changed = pyqtSignal(str, str)  # connection_id, state
    
    def __init__(self, max_connections: int = 5):
        super().__init__()
        self.max_connections = max_connections
        self.connections: Dict[str, ConnectionInfo] = {}
        self.transfer_queue = queue.PriorityQueue()
        self.active_jobs: Dict[str, TransferJob] = {}
        self.completed_jobs: List[TransferJob] = []
        
        # Connection parameters (set when first connection is established)
        self.host = ""
        self.port = 21
        self.username = ""
        self.password = ""
        self.passive_mode = True
        
        # Control flags
        self.is_running = False
        self.dispatcher_thread = None
        self._shutdown_event = threading.Event()
        
        # Statistics
        self.total_bytes_transferred = 0
        self.start_time = None
        
    def initialize_pool(self, host: str, port: int, username: str, password: str, passive_mode: bool = True):
        """Initialize the connection pool with server credentials"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.passive_mode = passive_mode
        
        # Start the dispatcher thread
        self.is_running = True
        self.start_time = time.time()
        self.dispatcher_thread = threading.Thread(target=self._dispatcher_loop, daemon=True)
        self.dispatcher_thread.start()
        
    def add_transfer_job(self, job: TransferJob):
        """Add a transfer job to the queue"""
        # Priority queue uses tuple (priority, job_id, job)
        # Lower priority number = higher priority
        self.transfer_queue.put((job.priority, job.job_id, job))
        
    def get_idle_connection(self) -> Optional[ConnectionInfo]:
        """Get an idle connection or create a new one if under limit"""
        # Find existing idle connection
        for conn in self.connections.values():
            if conn.state == ConnectionState.IDLE:
                return conn
        
        # Create new connection if under limit
        if len(self.connections) < self.max_connections:
            return self._create_connection()
        
        return None
    
    def _create_connection(self) -> Optional[ConnectionInfo]:
        """Create a new FTP connection"""
        if not ftp_engine:
            return None
            
        connection_id = f"conn_{len(self.connections) + 1}"
        
        try:
            client = ftp_engine.FtpClient()
            conn_info = ConnectionInfo(
                connection_id=connection_id,
                client=client,
                state=ConnectionState.CONNECTING
            )
            
            self.connections[connection_id] = conn_info
            self.connection_state_changed.emit(connection_id, ConnectionState.CONNECTING.value)
            
            # Connect in a separate thread
            def connect_worker():
                try:
                    if client.connect(self.host, self.port):
                        if client.login(self.username, self.password):
                            client.setPassive(self.passive_mode)
                            conn_info.state = ConnectionState.IDLE
                            conn_info.error_count = 0
                            self.connection_state_changed.emit(connection_id, ConnectionState.IDLE.value)
                            return
                    
                    # Connection failed
                    conn_info.state = ConnectionState.ERROR
                    conn_info.error_count += 1
                    self.connection_state_changed.emit(connection_id, ConnectionState.ERROR.value)
                    
                except Exception as e:
                    conn_info.state = ConnectionState.ERROR
                    conn_info.error_count += 1
                    self.connection_state_changed.emit(connection_id, ConnectionState.ERROR.value)
            
            thread = threading.Thread(target=connect_worker, daemon=True)
            thread.start()
            conn_info.thread = thread
            
            return conn_info
            
        except Exception as e:
            return None
    
    def _dispatcher_loop(self):
        """Main dispatcher loop that assigns jobs to connections"""
        while self.is_running and not self._shutdown_event.is_set():
            try:
                # Get next job from queue (blocking with timeout)
                try:
                    priority, job_id, job = self.transfer_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Find available connection
                conn = self.get_idle_connection()
                if conn is None:
                    # No connections available, put job back and wait
                    self.transfer_queue.put((priority, job_id, job))
                    time.sleep(0.1)
                    continue
                
                # Wait for connection to be ready
                max_wait = 10  # seconds
                wait_time = 0
                while conn.state == ConnectionState.CONNECTING and wait_time < max_wait:
                    time.sleep(0.1)
                    wait_time += 0.1
                
                if conn.state != ConnectionState.IDLE:
                    # Connection not ready, put job back
                    self.transfer_queue.put((priority, job_id, job))
                    continue
                
                # Assign job to connection
                conn.state = ConnectionState.BUSY
                conn.current_job = job
                self.active_jobs[job_id] = job
                
                # Start transfer in separate thread
                transfer_thread = threading.Thread(
                    target=self._execute_transfer,
                    args=(conn, job),
                    daemon=True
                )
                transfer_thread.start()
                
            except Exception as e:
                print(f"Dispatcher error: {e}")
                time.sleep(1)
    
    def _execute_transfer(self, conn: ConnectionInfo, job: TransferJob):
        """Execute a single transfer job"""
        try:
            self.job_started.emit(job.job_id)
            job.started_at = time.time()
            job.progress = 0.0
            job.speed = 0.0
            job.bytes_transferred = 0
            
            success = False
            error_message = ""
            
            if job.transfer_type == TransferType.UPLOAD:
                success = self._upload_file_with_progress(conn, job)
            else:  # DOWNLOAD
                success = self._download_file_with_progress(conn, job)
            
            if success:
                job.completed_at = time.time()
                job.progress = 100.0
                self.job_progress.emit(job.job_id, 100.0)
                self.job_completed.emit(job.job_id, True, "Transfer completed successfully")
            else:
                error_message = f"Transfer failed for {job.local_path}"
                job.error = error_message
                self.job_completed.emit(job.job_id, False, error_message)
                
        except Exception as e:
            error_message = f"Transfer error: {str(e)}"
            job.error = error_message
            self.job_completed.emit(job.job_id, False, error_message)
            
        finally:
            # Clean up
            conn.state = ConnectionState.IDLE
            conn.current_job = None
            conn.last_used = time.time()
            
            # Move job to completed list
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            self.completed_jobs.append(job)
            
            # Emit state change
            self.connection_state_changed.emit(conn.connection_id, ConnectionState.IDLE.value)
    
    def _upload_file(self, conn: ConnectionInfo, job: TransferJob) -> bool:
        """Upload a single file"""
        try:
            return conn.client.uploadFile(job.local_path, job.remote_path)
        except Exception as e:
            print(f"Upload error: {e}")
            return False
    
    def _download_file(self, conn: ConnectionInfo, job: TransferJob) -> bool:
        """Download a single file"""
        try:
            return conn.client.downloadFile(job.remote_path, job.local_path)
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    def _upload_file_with_progress(self, conn: ConnectionInfo, job: TransferJob) -> bool:
        """Upload a single file with progress tracking using C++ callbacks"""
        try:
            # Debug: Print the path being processed
            print(f"DEBUG: Connection Pool - Processing upload for path: {repr(job.local_path)}")
            
            # Normalize the path to handle Unicode characters properly
            job.local_path = os.path.normpath(job.local_path)
            
            # Check if file exists
            if not os.path.exists(job.local_path):
                print(f"ERROR: Connection Pool - File not found: {repr(job.local_path)}")
                return False
            
            # Get file size for progress calculation
            file_size = os.path.getsize(job.local_path)
            job.size = file_size
            job.started_at = time.time()
            job.bytes_transferred = 0
            job.speed = 0
            
            # Create progress callback function that will be called by C++
            def progress_callback(bytes_transferred: int, total_bytes: int):
                # Calculate progress percentage
                if total_bytes > 0:
                    progress = (bytes_transferred / total_bytes) * 100
                else:
                    progress = 0
                
                # Calculate speed (bytes per second)
                elapsed = time.time() - job.started_at
                if elapsed > 0:
                    speed = bytes_transferred / elapsed
                else:
                    speed = 0
                
                # Update job data with real values from C++
                job.progress = progress
                job.speed = speed
                job.bytes_transferred = bytes_transferred
                if total_bytes > 0:
                    job.size = total_bytes
                
                # Emit progress signal with real progress from C++
                self.job_progress.emit(job.job_id, progress)
            
            # Always use the C++ progress-aware upload function
            success = conn.client.uploadFileWithProgress(job.local_path, job.remote_path, progress_callback)
            
            if success:
                # Update total bytes transferred with actual transferred bytes
                self.total_bytes_transferred += job.bytes_transferred
                return True
            return False
                
        except Exception as e:
            print(f"Upload with progress error: {e}")
            return False
    
    def _download_file_with_progress(self, conn: ConnectionInfo, job: TransferJob) -> bool:
        """Download a single file with progress tracking using C++ callbacks"""
        try:
            job.started_at = time.time()
            job.bytes_transferred = 0
            job.speed = 0
            job.size = 0
            
            # Create progress callback function that will be called by C++
            def progress_callback(bytes_transferred: int, total_bytes: int):
                # Calculate progress percentage
                if total_bytes > 0:
                    progress = (bytes_transferred / total_bytes) * 100
                else:
                    # For downloads where total size is unknown, show bytes transferred
                    # We'll update this when we know the total size
                    progress = 0 if bytes_transferred == 0 else min(bytes_transferred / (1024 * 1024), 100)
                
                # Calculate speed (bytes per second)
                elapsed = time.time() - job.started_at
                if elapsed > 0:
                    speed = bytes_transferred / elapsed
                else:
                    speed = 0
                
                # Update job data with real values from C++
                job.progress = progress
                job.speed = speed
                job.bytes_transferred = bytes_transferred
                if total_bytes > 0:
                    job.size = total_bytes
                
                # Emit progress signal with real progress from C++
                self.job_progress.emit(job.job_id, progress)
            
            # Always use the C++ progress-aware download function
            success = conn.client.downloadFileWithProgress(job.remote_path, job.local_path, progress_callback)
            
            if success:
                # Update file size after download if not set by callback
                if job.size == 0 and os.path.exists(job.local_path):
                    job.size = os.path.getsize(job.local_path)
                    job.bytes_transferred = job.size
                
                # Update total bytes transferred with actual transferred bytes
                self.total_bytes_transferred += job.bytes_transferred
                return True
            return False
            
        except Exception as e:
            print(f"Download with progress error: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transfer statistics"""
        active_count = len(self.active_jobs)
        completed_count = len(self.completed_jobs)
        queue_size = self.transfer_queue.qsize()
        
        # Calculate speeds
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        avg_speed = self.total_bytes_transferred / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'active_connections': len([c for c in self.connections.values() if c.state == ConnectionState.IDLE]),
            'busy_connections': len([c for c in self.connections.values() if c.state == ConnectionState.BUSY]),
            'total_connections': len(self.connections),
            'active_transfers': active_count,
            'completed_transfers': completed_count,
            'queued_transfers': queue_size,
            'total_bytes_transferred': self.total_bytes_transferred,
            'average_speed': avg_speed,
            'elapsed_time': elapsed_time
        }
    
    def shutdown(self):
        """Shutdown the connection pool"""
        self.is_running = False
        self._shutdown_event.set()
        
        # Wait for dispatcher to finish
        if self.dispatcher_thread and self.dispatcher_thread.is_alive():
            self.dispatcher_thread.join(timeout=5)
        
        # Close all connections
        for conn in self.connections.values():
            try:
                if conn.client:
                    conn.client.disconnect()
            except:
                pass
        
        self.connections.clear()
        self.active_jobs.clear()
