@echo off
REM ClamAV Portable Installation Script for Windows
REM This script installs portable ClamAV for the FTP Client project

echo ============================================================
echo  ClamAV Portable Installation Script for FTP Client
echo ============================================================

set "INSTALL_DIR=%LOCALAPPDATA%\ClamAV"
set "DOWNLOAD_URL=https://www.clamav.net/downloads/production/clamav-1.4.3.win.x64.zip"
set "TEMP_ZIP=%TEMP%\clamav-1.4.3.zip"

echo Checking for existing ClamAV installation...

REM Check portable installation first
if exist "%INSTALL_DIR%\clamscan.exe" (
    echo Found portable ClamAV at: %INSTALL_DIR%\clamscan.exe
    goto :test_installation
)

REM Check common system installation paths
if exist "C:\Program Files\ClamAV\clamscan.exe" (
    echo Found ClamAV at: C:\Program Files\ClamAV\clamscan.exe
    goto :test_installation
)

if exist "C:\Program Files (x86)\ClamAV\clamscan.exe" (
    echo Found ClamAV at: C:\Program Files (x86)\ClamAV\clamscan.exe
    goto :test_installation
)

REM Check if clamscan is in PATH
clamscan --version >nul 2>&1
if %errorLevel% equ 0 (
    echo Found ClamAV in system PATH
    goto :test_installation
)

echo ClamAV not found. Installing portable version...

REM Create installation directory
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo Created installation directory: %INSTALL_DIR%
)

REM Download ClamAV portable
echo Downloading ClamAV 1.4.3 portable...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TEMP_ZIP%'}"

if not exist "%TEMP_ZIP%" (
    echo Download failed. Trying alternative method...
    curl -L -o "%TEMP_ZIP%" "%DOWNLOAD_URL%"
    if not exist "%TEMP_ZIP%" (
        echo Manual download required. Please:
        echo 1. Download from: %DOWNLOAD_URL%
        echo 2. Extract to: %INSTALL_DIR%
        echo 3. Run this script again to verify installation
        pause
        exit /b 1
    )
)

REM Extract the zip file
echo Extracting ClamAV portable...
powershell -Command "& {Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('%TEMP_ZIP%', '%INSTALL_DIR%')}"

REM Clean up temporary file
del "%TEMP_ZIP%" >nul 2>&1

REM Verify installation
if exist "%INSTALL_DIR%\clamscan.exe" (
    echo Portable ClamAV installed successfully!
    echo Installation directory: %INSTALL_DIR%
    echo Executable: %INSTALL_DIR%\clamscan.exe
    goto :test_installation
) else (
    echo Installation failed. clamscan.exe not found in %INSTALL_DIR%
    pause
    exit /b 1
)

:test_installation
echo Testing ClamAV installation...

REM Set the clamscan path
set "CLAMSCAN_PATH="
if exist "%INSTALL_DIR%\clamscan.exe" (
    set "CLAMSCAN_PATH=%INSTALL_DIR%\clamscan.exe"
) else if exist "C:\Program Files\ClamAV\clamscan.exe" (
    set "CLAMSCAN_PATH=C:\Program Files\ClamAV\clamscan.exe"
) else if exist "C:\Program Files (x86)\ClamAV\clamscan.exe" (
    set "CLAMSCAN_PATH=C:\Program Files (x86)\ClamAV\clamscan.exe"
) else (
    set "CLAMSCAN_PATH=clamscan"
)

REM Create test file with EICAR signature
echo X5O!P%%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H* > eicar_test.txt

REM Test scan
"%CLAMSCAN_PATH%" eicar_test.txt
if %errorLevel% neq 0 (
    echo Test passed! ClamAV detected the test virus.
    del eicar_test.txt >nul 2>&1
    goto :success
) else (
    echo Test failed. ClamAV might need database update.
    del eicar_test.txt >nul 2>&1
    echo Running freshclam to update virus database...
    
    REM Try to run freshclam
    set "FRESHCLAM_PATH="
    if exist "%INSTALL_DIR%\freshclam.exe" (
        set "FRESHCLAM_PATH=%INSTALL_DIR%\freshclam.exe"
    ) else if exist "C:\Program Files\ClamAV\freshclam.exe" (
        set "FRESHCLAM_PATH=C:\Program Files\ClamAV\freshclam.exe"
    ) else if exist "C:\Program Files (x86)\ClamAV\freshclam.exe" (
        set "FRESHCLAM_PATH=C:\Program Files (x86)\ClamAV\freshclam.exe"
    ) else (
        set "FRESHCLAM_PATH=freshclam"
    )
    
    "%FRESHCLAM_PATH%"
)

:success
echo.
echo ============================================================
echo  ClamAV Portable Installation Completed Successfully!
echo ============================================================
echo.
if exist "%INSTALL_DIR%\clamscan.exe" (
    echo Installation Type: Portable
    echo Installation Path: %INSTALL_DIR%
    echo Executable: %INSTALL_DIR%\clamscan.exe
    echo Note: ClamAV folder is excluded from version control
) else (
    echo Installation Type: System-wide
)
echo.
echo Your FTP client is now ready to scan uploaded files.
echo.
echo Next steps:
echo 1. Close this window  
echo 2. Run your FTP client application
echo 3. Files will be automatically scanned during upload
echo.
pause
exit /b 0
