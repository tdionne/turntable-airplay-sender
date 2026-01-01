#!/bin/bash
#
# Install Turntable AirPlay Sender as a systemd service
#

set -e

echo "Installing Turntable AirPlay Sender as a system service..."

# Check if running with appropriate privileges
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo ./install-service.sh"
    exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installation directory: $INSTALL_DIR"
echo "Running as user: $ACTUAL_USER"

# Update service file with correct paths
sed "s|/home/pi/turntable-airplay-sender|$INSTALL_DIR|g" turntable-airplay.service > /tmp/turntable-airplay.service.tmp
sed -i "s|User=pi|User=$ACTUAL_USER|g" /tmp/turntable-airplay.service.tmp

# Copy service file
cp /tmp/turntable-airplay.service.tmp /etc/systemd/system/turntable-airplay.service
rm /tmp/turntable-airplay.service.tmp

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable turntable-airplay.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start service:   sudo systemctl start turntable-airplay"
echo "  Stop service:    sudo systemctl stop turntable-airplay"
echo "  Check status:    sudo systemctl status turntable-airplay"
echo "  View logs:       sudo journalctl -u turntable-airplay -f"
echo "  Disable service: sudo systemctl disable turntable-airplay"
echo ""
echo "⚠️  Make sure to edit config.yaml before starting the service!"

