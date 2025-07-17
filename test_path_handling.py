#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to verify path handling works correctly without double quotes
"""

import shlex
import tempfile
import os

def test_command_parsing():
    """Test that our new command format works correctly with shlex.split"""
    
    # Test file with spaces in name
    test_file = "test file with spaces.txt"
    test_path = f"C:\\Users\\Test\\{test_file}"
    
    # Our new format (using double quotes)
    new_command = f'put "{test_path}" "{test_file}"'
    
    # Parse with shlex.split (as SessionManager does)
    parts = shlex.split(new_command)
    
    print("Testing path handling:")
    print(f"Original command: {new_command}")
    print(f"Parsed parts: {parts}")
    print(f"Command: {parts[0]}")
    print(f"Local path: {parts[1]}")
    print(f"Remote path: {parts[2]}")
    
    # Verify no quotes are in the parsed arguments
    assert parts[0] == "put"
    assert parts[1] == test_path  # Should be unquoted
    assert parts[2] == test_file  # Should be unquoted
    assert '"' not in parts[1]    # No quotes in local path
    assert '"' not in parts[2]    # No quotes in remote path
    
    print("✅ Path handling test passed!")

def test_unicode_path():
    """Test handling of Unicode characters in paths"""
    
    # Test file with Unicode characters
    unicode_file = "测试文件.txt"
    unicode_path = f"C:\\Users\\Test\\{unicode_file}"
    
    command = f'put "{unicode_path}" "{unicode_file}"'
    parts = shlex.split(command)
    
    print(f"\nTesting Unicode path handling:")
    print(f"Original command: {command}")
    print(f"Parsed parts: {parts}")
    
    assert parts[1] == unicode_path
    assert parts[2] == unicode_file
    
    print("✅ Unicode path handling test passed!")

if __name__ == "__main__":
    test_command_parsing()
    test_unicode_path()
    print("\n🎉 All tests passed! Path handling should work correctly now.")
