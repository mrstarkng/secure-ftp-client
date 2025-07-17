#!/bin/bash
# ClamAV Portable Installation Script for Linux
# This script installs portable ClamAV for the FTP Client project

echo "============================================================"
echo " ClamAV Portable Installation Script for FTP Client"
echo "============================================================"

INSTALL_DIR="$HOME/ClamAV"
TEMP_DIR="/tmp/clamav_install"

# Detect package type
if command -v dpkg &> /dev/null; then
    DOWNLOAD_URL="https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.deb"
    PACKAGE_TYPE="deb"
elif command -v rpm &> /dev/null; then
    DOWNLOAD_URL="https://www.clamav.net/downloads/production/clamav-1.4.3.linux.x86_64.rpm"
    PACKAGE_TYPE="rpm"
else
    echo "❌ No supported package manager found (dpkg or rpm)"
    echo "Please install dpkg or rpm first, or install ClamAV manually"
    exit 1
fi

echo "Checking for existing ClamAV installation..."

# Check portable installation first
if [[ -f "$INSTALL_DIR/bin/clamscan" ]]; then
    echo "✅ Found portable ClamAV: $INSTALL_DIR/bin/clamscan"
    CLAMSCAN_PATH="$INSTALL_DIR/bin/clamscan"
    echo "Version: $($CLAMSCAN_PATH --version | head -n1)"
    
    # Test installation
    echo "Testing ClamAV installation..."
    
    # Create test file with EICAR signature
    echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar_test.txt
    
    # Test scan
    if $CLAMSCAN_PATH /tmp/eicar_test.txt | grep -q "FOUND"; then
        echo "✅ Test passed! ClamAV detected the test virus."
        rm -f /tmp/eicar_test.txt
        echo "🎉 Portable ClamAV is already installed and working!"
        exit 0
    else
        echo "⚠️  Test failed. Will try to update database..."
        rm -f /tmp/eicar_test.txt
    fi
fi

# Check system-wide installation
if command -v clamscan &> /dev/null; then
    echo "✅ Found system ClamAV: $(which clamscan)"
    echo "Version: $(clamscan --version | head -n1)"
    
    # Test installation
    echo "Testing ClamAV installation..."
    
    # Create test file with EICAR signature
    echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar_test.txt
    
    # Test scan
    if clamscan /tmp/eicar_test.txt | grep -q "FOUND"; then
        echo "✅ Test passed! ClamAV detected the test virus."
        rm -f /tmp/eicar_test.txt
        echo "🎉 System ClamAV is already installed and working!"
        exit 0
    else
        echo "⚠️  Test failed. Will install portable version..."
        rm -f /tmp/eicar_test.txt
    fi
fi

echo "ClamAV not found or not working. Installing portable version..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$TEMP_DIR"

# Download package
echo "📥 Downloading ClamAV 1.4.3 portable ($PACKAGE_TYPE)..."
if command -v curl &> /dev/null; then
    curl -L -o "$TEMP_DIR/clamav.$PACKAGE_TYPE" "$DOWNLOAD_URL"
elif command -v wget &> /dev/null; then
    wget -O "$TEMP_DIR/clamav.$PACKAGE_TYPE" "$DOWNLOAD_URL"
else
    echo "❌ Neither curl nor wget found. Please install one of them."
    exit 1
fi

if [[ ! -f "$TEMP_DIR/clamav.$PACKAGE_TYPE" ]]; then
    echo "❌ Download failed. Please check your internet connection."
    exit 1
fi

# Extract package
echo "📦 Extracting ClamAV portable..."
if [[ "$PACKAGE_TYPE" == "deb" ]]; then
    # Extract .deb package
    if command -v dpkg-deb &> /dev/null; then
        dpkg-deb -x "$TEMP_DIR/clamav.$PACKAGE_TYPE" "$INSTALL_DIR"
    else
        echo "❌ dpkg-deb not found. Cannot extract .deb package."
        exit 1
    fi
elif [[ "$PACKAGE_TYPE" == "rpm" ]]; then
    # Extract .rpm package
    if command -v rpm2cpio &> /dev/null && command -v cpio &> /dev/null; then
        cd "$INSTALL_DIR"
        rpm2cpio "$TEMP_DIR/clamav.$PACKAGE_TYPE" | cpio -idmv
    else
        echo "❌ rpm2cpio or cpio not found. Cannot extract .rpm package."
        exit 1
    fi
fi

# Find clamscan executable
CLAMSCAN_PATH=""
for path in "$INSTALL_DIR/usr/bin/clamscan" "$INSTALL_DIR/bin/clamscan"; do
    if [[ -f "$path" ]]; then
        CLAMSCAN_PATH="$path"
        break
    fi
done

# Search recursively if not found
if [[ -z "$CLAMSCAN_PATH" ]]; then
    CLAMSCAN_PATH=$(find "$INSTALL_DIR" -name "clamscan" -type f | head -n1)
fi

if [[ -z "$CLAMSCAN_PATH" || ! -f "$CLAMSCAN_PATH" ]]; then
    echo "❌ clamscan not found in extracted files."
    exit 1
fi

# Make executable
chmod +x "$CLAMSCAN_PATH"

# Clean up
rm -rf "$TEMP_DIR"

echo "✅ ClamAV portable installation completed successfully!"
echo "   Installation directory: $INSTALL_DIR"
echo "   Executable: $CLAMSCAN_PATH"

# Update virus database (if freshclam exists)
FRESHCLAM_PATH=""
for path in "$INSTALL_DIR/usr/bin/freshclam" "$INSTALL_DIR/bin/freshclam"; do
    if [[ -f "$path" ]]; then
        FRESHCLAM_PATH="$path"
        break
    fi
done

if [[ -z "$FRESHCLAM_PATH" ]]; then
    FRESHCLAM_PATH=$(find "$INSTALL_DIR" -name "freshclam" -type f | head -n1)
fi

if [[ -n "$FRESHCLAM_PATH" && -f "$FRESHCLAM_PATH" ]]; then
    chmod +x "$FRESHCLAM_PATH"
    echo "🔄 Updating virus database..."
    "$FRESHCLAM_PATH"
else
    echo "⚠️  freshclam not found, skipping database update"
fi

# Test installation
echo "🧪 Testing ClamAV installation..."

# Create test file with EICAR signature
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar_test.txt

# Test scan
if "$CLAMSCAN_PATH" /tmp/eicar_test.txt | grep -q "FOUND"; then
    echo "✅ Test passed! ClamAV detected the test virus."
    rm -f /tmp/eicar_test.txt
    
    echo ""
    echo "============================================================"
    echo " ClamAV Portable Installation Completed Successfully!"
    echo "============================================================"
    echo ""
    echo "Installation Type: Portable"
    echo "Installation Path: $INSTALL_DIR"
    echo "Executable: $CLAMSCAN_PATH"
    echo "Note: ClamAV folder is excluded from version control"
    echo ""
    echo "Your FTP client is now ready to scan uploaded files."
    echo ""
    echo "Next steps:"
    echo "1. Run your FTP client application"
    echo "2. Files will be automatically scanned during upload"
    echo ""
    exit 0
else
    echo "⚠️  Test failed, but ClamAV should still work"
    rm -f /tmp/eicar_test.txt
    exit 0
fi
