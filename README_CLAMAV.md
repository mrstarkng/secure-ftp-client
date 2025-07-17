# ClamAV Automatic Installation for FTP Client

The FTP client now automatically handles ClamAV installation - **no manual setup required!**

## Automatic Installation

When you run the FTP client (`python main.py`), it will automatically:

1. **Check for existing ClamAV** - Looks for portable or system installations
2. **Download and install if needed** - Downloads official ClamAV 1.4.3 portable
3. **Test the installation** - Verifies virus scanning works
4. **Continue seamlessly** - Starts the application with antivirus protection

**No user interaction needed!** The process is completely automatic and transparent.

## What You'll See

### First Time (Installation Required)
```
Secure FTP Client

Setting up antivirus protection...
[Progress bar shows download and installation]
Antivirus protection ready!
```

### Subsequent Runs (Already Installed)
```
Secure FTP Client

Antivirus protection ready!
```

### If Installation Fails
```
Secure FTP Client

Starting without antivirus protection...
[Warning dialog explains the situation]
```

## Manual Installation (Optional)

If you prefer to install ClamAV manually or the automatic installation fails:

### Windows Users
1. Double-click on `install_clamav.bat`
2. Follow the on-screen instructions

### Linux Users
1. Make executable: `chmod +x install_clamav.sh`
2. Run: `./install_clamav.sh`

### Python Script
```bash
python setup_clamav.py
```

## Installation Paths

### Windows
- **Portable**: `%LOCALAPPDATA%\ClamAV\` (e.g., `C:\Users\YourName\AppData\Local\ClamAV\`)
- **Executable**: `%LOCALAPPDATA%\ClamAV\clamscan.exe`

### Linux
- **Portable**: `$HOME/ClamAV/` (e.g., `/home/username/ClamAV/`)
- **Executable**: `$HOME/ClamAV/usr/bin/clamscan` or `$HOME/ClamAV/bin/clamscan`

## Direct Download Links

The scripts use these official ClamAV portable releases:

- **Windows**: https://www.clamav.net/downloads/production/clamav-1.4.3.win.x64.zip
- **Linux DEB**: https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.deb
- **Linux RPM**: https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.rpm

## Manual Installation

If the automatic scripts don't work, you can install manually:

### Windows
1. Download: https://www.clamav.net/downloads/production/clamav-1.4.3.win.x64.zip
2. Extract to `%LOCALAPPDATA%\ClamAV\`
3. Test with: `%LOCALAPPDATA%\ClamAV\clamscan.exe --version`

### Linux
1. Download the appropriate package (DEB or RPM)
2. Extract to `$HOME/ClamAV/`
3. Make executable: `chmod +x $HOME/ClamAV/usr/bin/clamscan`
4. Test with: `$HOME/ClamAV/usr/bin/clamscan --version`

## Verification

After installation, verify ClamAV is working:

1. **Check version**: 
   - Windows: `%LOCALAPPDATA%\ClamAV\clamscan.exe --version`
   - Linux: `$HOME/ClamAV/usr/bin/clamscan --version`

2. **Create test file**: 
   ```bash
   echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > test.txt
   ```

3. **Scan test file**:
   - Windows: `%LOCALAPPDATA%\ClamAV\clamscan.exe test.txt`
   - Linux: `$HOME/ClamAV/usr/bin/clamscan test.txt`

4. **Expected output**: `test.txt: Eicar-Test-Signature FOUND`

## Troubleshooting

### Common Issues

**"File not found" or "clamscan not recognized"**
- ClamAV portable installation may have failed
- Check if the executable exists in the expected location
- Re-run the installation script

**"Permission denied"**
- On Linux, ensure the clamscan executable has execute permissions
- Run: `chmod +x $HOME/ClamAV/usr/bin/clamscan`

**"Download failed"**
- Check internet connection
- Verify the download URLs are accessible
- Try manual download and extraction

**Virus database is outdated**
- Run `freshclam` manually from the portable installation
- Windows: `%LOCALAPPDATA%\ClamAV\freshclam.exe`
- Linux: `$HOME/ClamAV/usr/bin/freshclam`

### **Advantages of Portable Installation**

- **No admin privileges required** - installs in user directory
- **Self-contained** - doesn't affect system installations
- **Consistent** - same version across all systems
- **Isolated** - can be easily removed by deleting the folder
- **Latest version** - always installs ClamAV 1.4.3
- **Version control friendly** - installation folders are excluded from git

### Getting Help

1. Check ClamAV documentation: https://docs.clamav.net/
2. Verify your system meets ClamAV requirements
3. Check firewall settings if database updates fail
4. Ensure the portable installation directory is writable

## Integration with FTP Client

The C++ backend automatically detects portable ClamAV installations:

1. **Windows**: Checks `%LOCALAPPDATA%\ClamAV\clamscan.exe` first
2. **Linux**: Checks `$HOME/ClamAV/usr/bin/clamscan` first
3. **Fallback**: Checks system installations and PATH

Your FTP client will automatically:
- Scan files before uploading to FTP server
- Display scan results in the application
- Block infected files from being uploaded
- Show detailed virus information if threats are found

## Security Notes

- **Local processing only** - no data sent to external servers
- **Portable database** - virus definitions stored locally
- **Regular updates** - run freshclam regularly for latest signatures
- **Test regularly** - verify scanning works with EICAR test file

## Files Included

- `setup_clamav.py` - Cross-platform Python installation script
- `install_clamav.bat` - Windows batch installation script (portable)
- `install_clamav.sh` - Linux shell installation script (portable)
- `README_CLAMAV.md` - This documentation file

## Version Control

The portable ClamAV installation directories are automatically excluded from version control via `.gitignore`:

- `**/ClamAV/` - Any ClamAV directory
- `clamav-*.zip`, `clamav-*.deb`, `clamav-*.rpm` - Download files
- `eicar_test.txt` - Test files created during installation

This ensures that:
- Binary files don't bloat your repository
- Each developer can have their own ClamAV installation
- Installation paths are user-specific and don't conflict
- The repository remains clean and focused on source code

## Requirements

- **Windows**: PowerShell (built-in), curl or PowerShell web commands
- **Linux**: curl or wget, dpkg-deb (for DEB) or rpm2cpio/cpio (for RPM)
- **Internet connection** for downloading ClamAV and virus database
- **~100MB disk space** for ClamAV and virus database
- **No administrator privileges required**
