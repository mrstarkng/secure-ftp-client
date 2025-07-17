# Test script for async virus scanner
import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from virus_scanner import get_virus_scanner
import time

def test_async_scanner():
    app = QApplication(sys.argv)
    
    scanner = get_virus_scanner(max_concurrent_scans=3)
    
    def on_scan_complete(file_path, result):
        print(f"Scan completed for {file_path}: {result}")
    
    # Test with a few files
    test_files = [
        "main.py",
        "session_manager.py", 
        "gui_widget.py"
    ]
    
    print("Starting async scans...")
    for test_file in test_files:
        if os.path.exists(test_file):
            job_id = scanner.scan_file_async(test_file, on_scan_complete)
            print(f"Queued scan job {job_id} for {test_file}")
    
    # Wait for scans to complete
    print("Waiting for scans to complete...")
    for i in range(30):  # Wait up to 30 seconds
        stats = scanner.get_stats()
        print(f"Scanner stats: {stats}")
        if stats['queue_size'] == 0 and stats['active_threads'] == 0:
            print("All scans completed!")
            break
        time.sleep(1)
        app.processEvents()
    
    scanner.shutdown()
    print("Test completed")

if __name__ == "__main__":
    test_async_scanner()
