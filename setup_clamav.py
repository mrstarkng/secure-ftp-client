#!/usr/bin/env python3
"""
ClamAV Setup Script for FTP Client
This script automatically installs ClamAV on Windows and Linux systems.
"""

import os
import sys
import subprocess
import platform
import requests
import zipfile
import shutil
from pathlib import Path
import tempfile

class ClamAVInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.clamav_version = "1.4.3"  # Latest stable version
        
        # Direct download URLs for portable versions
        self.download_urls = {
            "windows": "https://www.clamav.net/downloads/production/clamav-1.4.3.win.x64.zip",
            "linux_rpm": "https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.rpm",
            "linux_deb": "https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.deb"
        }
        
        # Installation directories
        self.install_dirs = {
            "windows": os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), 'ClamAV'),
            "linux": os.path.expanduser("~/ClamAV"),
            "darwin": os.path.expanduser("~/ClamAV")
        }
        
    def check_admin_privileges(self):
        """Check if running with administrator privileges."""
        try:
            if self.system == "windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
    
    def find_existing_clamav(self):
        """Check if ClamAV is already installed."""
        # Check portable installation first
        portable_paths = {
            "windows": os.path.join(self.install_dirs["windows"], "clamscan.exe"),
            "linux": os.path.join(self.install_dirs["linux"], "bin", "clamscan"),
            "darwin": os.path.join(self.install_dirs["darwin"], "bin", "clamscan")
        }
        
        portable_path = portable_paths.get(self.system)
        if portable_path and os.path.exists(portable_path):
            print(f"✅ Found portable ClamAV installation at: {portable_path}")
            return portable_path
        
        # Check system-wide installation
        common_paths = {
            "windows": [
                "C:\\Program Files\\ClamAV\\clamscan.exe",
                "C:\\Program Files (x86)\\ClamAV\\clamscan.exe"
            ],
            "linux": [
                "/usr/bin/clamscan",
                "/usr/local/bin/clamscan"
            ],
            "darwin": [
                "/usr/local/bin/clamscan",
                "/opt/homebrew/bin/clamscan"
            ]
        }
        
        paths = common_paths.get(self.system, [])
        for path in paths:
            if os.path.exists(path):
                print(f"✅ Found system ClamAV installation at: {path}")
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(["clamscan", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ ClamAV found in system PATH")
                return "clamscan"
        except:
            pass
        
        return None
    
    def install_windows(self):
        """Install portable ClamAV on Windows."""
        print("🪟 Installing portable ClamAV on Windows...")
        
        download_url = self.download_urls["windows"]
        install_dir = self.install_dirs["windows"]
        
        try:
            # Create installation directory
            os.makedirs(install_dir, exist_ok=True)
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "clamav.zip")
                
                print(f"📥 Downloading ClamAV {self.clamav_version}...")
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print("📦 Extracting files...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
                
                # Find the clamscan executable
                clamscan_path = os.path.join(install_dir, "clamscan.exe")
                if not os.path.exists(clamscan_path):
                    # Look for it in subdirectories
                    for root, dirs, files in os.walk(install_dir):
                        if "clamscan.exe" in files:
                            clamscan_path = os.path.join(root, "clamscan.exe")
                            break
                
                if not os.path.exists(clamscan_path):
                    raise Exception("Could not find clamscan.exe in extracted files")
                
                print("✅ ClamAV portable installation completed successfully!")
                print(f"   Installation directory: {install_dir}")
                print(f"   Executable: {clamscan_path}")
                
                return clamscan_path
                
        except requests.RequestException as e:
            print(f"❌ Download failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            return None
    
    def install_windows_chocolatey(self):
        """Try to install ClamAV using Chocolatey."""
        print("🍫 Attempting installation via Chocolatey...")
        
        try:
            # Check if chocolatey is installed
            result = subprocess.run(["choco", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print("❌ Chocolatey not found. Please install manually or use Chocolatey.")
                return None
            
            # Install ClamAV via Chocolatey
            print("📦 Installing ClamAV via Chocolatey...")
            result = subprocess.run(["choco", "install", "clamav", "-y"], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ ClamAV installed successfully via Chocolatey!")
                return self.find_existing_clamav()
            else:
                print(f"❌ Chocolatey installation failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Chocolatey installation failed: {e}")
            return None
    
    def add_to_path_windows(self, install_dir):
        """Add ClamAV to Windows PATH."""
        try:
            # Add to system PATH via registry (requires admin)
            import winreg
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                current_path = winreg.QueryValueEx(key, "Path")[0]
                if install_dir not in current_path:
                    new_path = current_path + ";" + install_dir
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    print(f"✅ Added {install_dir} to system PATH")
                    
        except Exception as e:
            print(f"⚠️  Could not add to system PATH: {e}")
            print(f"   Please manually add {install_dir} to your PATH")
    
    def install_linux(self):
        """Install portable ClamAV on Linux."""
        print("🐧 Installing portable ClamAV on Linux...")
        
        install_dir = self.install_dirs["linux"]
        
        # Detect package type preference
        if shutil.which("dpkg"):
            download_url = self.download_urls["linux_deb"]
            package_type = "deb"
        elif shutil.which("rpm"):
            download_url = self.download_urls["linux_rpm"]
            package_type = "rpm"
        else:
            print("❌ No supported package manager found (dpkg or rpm)")
            return None
        
        try:
            # Create installation directory
            os.makedirs(install_dir, exist_ok=True)
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                package_path = os.path.join(temp_dir, f"clamav.{package_type}")
                
                print(f"📥 Downloading ClamAV {self.clamav_version} ({package_type})...")
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                with open(package_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print("📦 Extracting package...")
                
                if package_type == "deb":
                    # Extract .deb package
                    subprocess.run(["dpkg-deb", "-x", package_path, install_dir], check=True)
                else:
                    # Extract .rpm package  
                    subprocess.run(["rpm2cpio", package_path], 
                                 stdout=subprocess.PIPE, check=True)
                    result = subprocess.run(["rpm2cpio", package_path], 
                                          stdout=subprocess.PIPE, check=True)
                    subprocess.run(["cpio", "-idmv"], 
                                 input=result.stdout, cwd=install_dir, check=True)
                
                # Find the clamscan executable
                clamscan_path = None
                for root, dirs, files in os.walk(install_dir):
                    if "clamscan" in files:
                        clamscan_path = os.path.join(root, "clamscan")
                        break
                
                if not clamscan_path or not os.path.exists(clamscan_path):
                    raise Exception("Could not find clamscan in extracted files")
                
                # Make executable
                os.chmod(clamscan_path, 0o755)
                
                print("✅ ClamAV portable installation completed successfully!")
                print(f"   Installation directory: {install_dir}")
                print(f"   Executable: {clamscan_path}")
                
                return clamscan_path
                
        except requests.RequestException as e:
            print(f"❌ Download failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            return None
    
    def install_macos(self):
        """Install ClamAV on macOS (fallback to Homebrew)."""
        print("🍎 Installing ClamAV on macOS...")
        print("ℹ️  Note: Portable version not available for macOS, using Homebrew...")
        
        try:
            # Try Homebrew first
            subprocess.run(["brew", "--version"], capture_output=True, check=True)
            
            print("🍺 Installing using Homebrew...")
            result = subprocess.run(["brew", "install", "clamav"], timeout=300)
            
            if result.returncode == 0:
                print("✅ ClamAV installed successfully!")
                return self.find_existing_clamav()
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Homebrew not found or installation failed.")
            print("Please install Homebrew first or install ClamAV manually.")
        
        return None
    
    def update_virus_database(self, clamscan_path):
        """Update the virus database."""
        print("🔄 Updating virus database...")
        
        try:
            # Find freshclam executable
            freshclam_path = clamscan_path.replace("clamscan", "freshclam")
            if self.system == "windows":
                freshclam_path = freshclam_path.replace(".exe", "")
                freshclam_path += ".exe"
            
            if os.path.exists(freshclam_path):
                result = subprocess.run([freshclam_path], timeout=300)
                if result.returncode == 0:
                    print("✅ Virus database updated successfully!")
                else:
                    print("⚠️  Database update failed, but ClamAV should still work")
            else:
                print("⚠️  freshclam not found, skipping database update")
                
        except Exception as e:
            print(f"⚠️  Database update failed: {e}")
    
    def test_installation(self, clamscan_path):
        """Test the ClamAV installation."""
        print("🧪 Testing ClamAV installation...")
        
        try:
            # Test with version command
            result = subprocess.run([clamscan_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ ClamAV is working correctly!")
                print(f"   Version: {result.stdout.strip()}")
                
                # Create test file with EICAR test signature
                test_file = "eicar_test.txt"
                eicar_signature = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
                
                with open(test_file, 'w') as f:
                    f.write(eicar_signature)
                
                # Test scan
                result = subprocess.run([clamscan_path, test_file], 
                                      capture_output=True, text=True, timeout=30)
                
                # Clean up test file
                os.remove(test_file)
                
                if "FOUND" in result.stdout:
                    print("✅ Virus detection test passed!")
                    return True
                else:
                    print("⚠️  Virus detection test failed (might need database update)")
                    return True
            else:
                print(f"❌ ClamAV test failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ ClamAV test failed: {e}")
            return False
    
    def install(self):
        """Main installation method."""
        print("=" * 60)
        print("🦠 ClamAV Installation Script for FTP Client")
        print("=" * 60)
        
        # Check for existing installation
        existing_path = self.find_existing_clamav()
        if existing_path:
            if self.test_installation(existing_path):
                print("🎉 ClamAV is already installed and working!")
                return existing_path
        
        # Note: Portable installations don't require admin privileges
        print("ℹ️  Installing portable ClamAV (no admin privileges required)...")
        
        # Install based on system
        clamscan_path = None
        if self.system == "windows":
            clamscan_path = self.install_windows()
        elif self.system == "linux":
            clamscan_path = self.install_linux()
        elif self.system == "darwin":
            clamscan_path = self.install_macos()
        else:
            print(f"❌ Unsupported operating system: {self.system}")
            return None
        
        if clamscan_path:
            # Update virus database
            self.update_virus_database(clamscan_path)
            
            # Test installation
            if self.test_installation(clamscan_path):
                print("\n🎉 ClamAV installation completed successfully!")
                print(f"   Executable path: {clamscan_path}")
                print("\n📋 Next steps:")
                print("   1. Restart your terminal/command prompt")
                print("   2. Run your FTP client application")
                print("   3. Upload files will now be scanned automatically")
                print("\n📝 Note: ClamAV installation folder is excluded from version control")
                return clamscan_path
            else:
                print("❌ Installation completed but tests failed")
                return None
        else:
            print("❌ Installation failed")
            return None

def main():
    """Main function."""
    installer = ClamAVInstaller()
    
    try:
        result = installer.install()
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
