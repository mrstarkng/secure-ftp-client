"""
Automatic ClamAV installer module for FTP Client
This module handles automatic ClamAV installation and setup without user intervention
"""

import os
import sys
import subprocess
import platform
import tempfile
import shutil
import time
from pathlib import Path
import zipfile
import requests
from PyQt6.QtWidgets import QProgressDialog, QMessageBox, QApplication
from PyQt6.QtCore import QThread, pyqtSignal, Qt

def update_clamav_database(clamscan_path, status_callback=None):
    """Run freshclam to update the virus database."""
    try:
        if not clamscan_path:
            return False, "ClamAV path not found."

        clamav_dir = os.path.dirname(clamscan_path)
        freshclam_exe = "freshclam.exe" if platform.system() == "Windows" else "freshclam"
        freshclam_path = os.path.join(clamav_dir, freshclam_exe)

        if not os.path.exists(freshclam_path):
            return False, f"{freshclam_exe} not found in {clamav_dir}"

        if status_callback:
            status_callback("Updating virus definitions (this may take a few minutes)...")

        # The portable version needs a database directory with proper permissions
        db_dir = os.path.join(clamav_dir, "database")
        
        # Ensure database directory exists and is writable
        try:
            os.makedirs(db_dir, exist_ok=True)
            # Test write access
            test_file = os.path.join(db_dir, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            return False, f"Database directory {db_dir} is not writable: {e}"

        # Use --datadir parameter instead of config file
        command = [freshclam_path, f"--datadir={db_dir}", "--show-progress", "--verbose"]
        
        if status_callback:
            status_callback("Starting virus database download...")
        
        # Set working directory to the clamav directory
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8',
            errors='replace',  # Handle encoding errors gracefully
            cwd=clamav_dir
        )

        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                output_lines.append(line)
                if status_callback and line:
                    # Show only relevant progress messages
                    if any(keyword in line.lower() for keyword in ['downloading', 'updated', 'bytecode', 'main.cvd', 'daily.cvd', 'received']):
                        status_callback(f"Database update: {line}")
        
        success = process.poll() == 0
        if success:
            # Verify that database files were actually downloaded
            db_files = [f for f in os.listdir(db_dir) if f.endswith(('.cvd', '.cld'))]
            if db_files:
                return True, f"Database updated successfully. Downloaded {len(db_files)} definition files."
            else:
                return False, "Database update completed but no definition files found."
        else:
            error_output = "\n".join(output_lines[-10:])  # Last 10 lines
            return False, f"Failed to update database. Output: {error_output}"

    except Exception as e:
        return False, f"Failed to update database: {e}"

class ClamAVInstaller(QThread):
    """Thread-based ClamAV installer to avoid blocking the GUI"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    installation_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = platform.system().lower()
        self.clamav_version = "1.4.3"
        
        # Download URLs
        self.download_urls = {
            "windows": "https://www.clamav.net/downloads/production/clamav-1.4.3.win.x64.zip",
            "linux_deb": "https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.deb",
            "linux_rpm": "https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.rpm"
        }
        
        # Installation paths - use project root instead of user directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if self.system == "windows":
            self.install_dir = os.path.join(project_root, 'clamav-portable')
        else:
            self.install_dir = os.path.join(project_root, 'clamav-portable')
    
    def find_existing_clamav(self):
        """Check if ClamAV is already installed"""
        # Check portable installation in project root first
        if self.system == "windows":
            # Check for clamscan.exe in the root of install_dir and also in a versioned subfolder
            possible_portable_paths = [
                os.path.join(self.install_dir, "clamscan.exe"),
                os.path.join(self.install_dir, f"clamav-{self.clamav_version}.win.x64", "clamscan.exe")
            ]
            portable_path = None
            for path in possible_portable_paths:
                if os.path.exists(path):
                    portable_path = path
                    break
        else:
            portable_paths = [
                os.path.join(self.install_dir, "usr", "bin", "clamscan"),
                os.path.join(self.install_dir, "bin", "clamscan"),
            ]
            portable_path = None
            for path in portable_paths:
                if os.path.exists(path):
                    portable_path = path
                    break
        
        if portable_path and os.path.exists(portable_path):
            return portable_path
        
        # Check system-wide installation
        try:
            result = subprocess.run(["clamscan", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "clamscan"  # Available in system PATH
        except:
            pass
            
        return None
    
    def download_file(self, url, dest_path):
        """Download file with progress"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 50)  # 50% for download
                            self.progress_updated.emit(progress)
            
            # Ensure file is closed properly before returning
            response.close()
            return True
        except Exception as e:
            self.status_updated.emit(f"Download failed: {str(e)}")
            return False
    
    def install_windows(self):
        """Install ClamAV on Windows"""
        download_url = self.download_urls["windows"]
        
        # Use project root directory instead of temp directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        zip_path = os.path.join(project_root, "clamav-1.4.3.win.x64.zip")
        
        # Check if file already exists to skip download
        if not os.path.exists(zip_path):
            self.status_updated.emit("Downloading ClamAV...")
            if not self.download_file(download_url, zip_path):
                return False
        else:
            self.status_updated.emit("Using existing ClamAV archive...")
            self.progress_updated.emit(50)
        
        self.status_updated.emit("Extracting ClamAV...")
        self.progress_updated.emit(60)
        
        # Create installation directory
        os.makedirs(self.install_dir, exist_ok=True)
        
        # Extract zip file with proper cleanup
        zip_file = None
        try:
            zip_file = zipfile.ZipFile(zip_path, 'r')
            zip_file.extractall(self.install_dir)
            zip_file.close()
            zip_file = None
            
            # Verify installation
            clamscan_path = os.path.join(self.install_dir, "clamscan.exe")
            if os.path.exists(clamscan_path):
                self.progress_updated.emit(90)
                return True
            else:
                self.status_updated.emit("Installation failed: clamscan.exe not found")
                return False
                
        except Exception as e:
            if zip_file:
                try:
                    zip_file.close()
                except:
                    pass
            self.status_updated.emit(f"Extraction failed: {str(e)}")
            return False
    
    def install_linux(self):
        """Install ClamAV on Linux"""
        # Detect package type
        if shutil.which("dpkg-deb"):
            download_url = self.download_urls["linux_deb"]
            package_type = "deb"
        elif shutil.which("rpm2cpio") and shutil.which("cpio"):
            download_url = self.download_urls["linux_rpm"]
            package_type = "rpm"
        else:
            self.status_updated.emit("No supported package tools found")
            return False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = os.path.join(temp_dir, f"clamav.{package_type}")
            
            self.status_updated.emit("Downloading ClamAV...")
            if not self.download_file(download_url, package_path):
                return False
            
            self.status_updated.emit("Extracting ClamAV...")
            self.progress_updated.emit(60)
            
            try:
                # Create installation directory
                os.makedirs(self.install_dir, exist_ok=True)
                
                # Extract package
                if package_type == "deb":
                    subprocess.run(["dpkg-deb", "-x", package_path, self.install_dir], check=True)
                else:
                    # Extract RPM
                    result = subprocess.run(["rpm2cpio", package_path], 
                                          stdout=subprocess.PIPE, check=True)
                    subprocess.run(["cpio", "-idmv"], 
                                 input=result.stdout, cwd=self.install_dir, check=True)
                
                # Find and verify clamscan
                clamscan_path = None
                for root, dirs, files in os.walk(self.install_dir):
                    if "clamscan" in files:
                        clamscan_path = os.path.join(root, "clamscan")
                        break
                
                if clamscan_path and os.path.exists(clamscan_path):
                    # Make executable
                    os.chmod(clamscan_path, 0o755)
                    self.progress_updated.emit(90)
                    return True
                else:
                    self.status_updated.emit("Installation failed: clamscan not found")
                    return False
                    
            except Exception as e:
                self.status_updated.emit(f"Extraction failed: {str(e)}")
                return False
    
    def test_installation(self, clamscan_path):
        """Test ClamAV installation with EICAR test"""
        try:
            self.status_updated.emit("Testing ClamAV installation...")
            
            # Create EICAR test file
            eicar_content = 'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
            test_file = os.path.join(tempfile.gettempdir(), "eicar_test.txt")
            
            with open(test_file, 'w') as f:
                f.write(eicar_content)
            
            # Run scan
            result = subprocess.run([clamscan_path, test_file], 
                                  capture_output=True, text=True, timeout=30)
            
            # Clean up test file
            try:
                os.remove(test_file)
            except:
                pass
            
            # Check if virus was detected
            if result.returncode != 0 and "FOUND" in result.stdout:
                return True
            else:
                # Test passed even if no virus detected (database might be empty)
                return False 
                
        except Exception as e:
            self.status_updated.emit(f"Test failed: {str(e)}")
            return False
    
    def run(self):
        """Main installation thread"""
        try:
            # Check if already installed
            existing_path = self.find_existing_clamav()
            if existing_path:
                self.progress_updated.emit(100)
                self.installation_completed.emit(True, f"ClamAV found at: {existing_path}")
                return
            
            # Install based on platform
            success = False
            if self.system == "windows":
                success = self.install_windows()
            elif self.system == "linux":
                success = self.install_linux()
            else:
                self.installation_completed.emit(False, f"Unsupported platform: {self.system}")
                return
            
            if success:
                # Test installation
                clamscan_path = self.find_existing_clamav()
                if clamscan_path and self.test_installation(clamscan_path):
                    self.progress_updated.emit(100)
                    self.installation_completed.emit(True, f"ClamAV installed successfully at: {clamscan_path}")
                else:
                    self.installation_completed.emit(False, "Installation completed but tests failed")
            else:
                self.installation_completed.emit(False, "Installation failed")
                
        except Exception as e:
            self.installation_completed.emit(False, f"Unexpected error: {str(e)}")

def ensure_clamav_installed(parent=None):
    """
    Ensure ClamAV is installed, with GUI feedback if needed
    Returns True if ClamAV is available, False otherwise
    """
    installer = ClamAVInstaller()
    
    # Check if already installed
    existing_path = installer.find_existing_clamav()
    if existing_path:
        return True
    
    # For now, skip automatic installation and just return False
    # This allows the application to start without ClamAV
    try:
        # Show progress dialog
        progress_dialog = QProgressDialog("Setting up ClamAV antivirus...", None, 0, 100, parent)
        progress_dialog.setWindowTitle("FTP Client Setup")
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.show()
        
        # Connect signals
        installer.progress_updated.connect(progress_dialog.setValue)
        installer.status_updated.connect(progress_dialog.setLabelText)
        
        # Track installation result
        installation_result = {"success": False, "message": ""}
        
        def on_installation_completed(success, message):
            installation_result["success"] = success
            installation_result["message"] = message
            progress_dialog.close()
        
        installer.installation_completed.connect(on_installation_completed)
        
        # Start installation
        installer.start()
        
        # Wait for completion with timeout
        installer.wait(30000)  # 30 second timeout
        
        if installer.isRunning():
            installer.terminate()
            installer.wait()
            return False
        
        # Show result
        if installation_result["success"]:
            return True
        else:
            # Show error message only if there was a real attempt
            if installation_result["message"]:
                QMessageBox.warning(parent, "ClamAV Setup Failed", 
                              f"Failed to install ClamAV: {installation_result['message']}\n\n"
                              "The application will continue without virus scanning.")
            return False
            
    except Exception as e:
        # Log error but don't show dialog - just continue without ClamAV
        print(f"ClamAV installation error: {e}")
        return False

def get_clamav_path():
    """Get the path to ClamAV executable"""
    installer = ClamAVInstaller()
    return installer.find_existing_clamav()
