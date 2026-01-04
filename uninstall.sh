#!/bin/bash
#
# Uninstall Turntable Streaming Server
#

set -e

# Configuration
INSTALL_DIR="/opt/turntable-streaming"
CONFIG_DIR="/etc/turntable-streaming"
DOC_DIR="/usr/share/doc/turntable-streaming"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=========================================="
echo "Turntable Streaming Server - Uninstall"
echo -e "==========================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root: sudo ./uninstall.sh${NC}"
    exit 1
fi

# Stop and disable services
echo "Stopping services..."
systemctl stop turntable-stream 2>/dev/null || true
systemctl disable turntable-stream 2>/dev/null || true
systemctl stop turntable-web 2>/dev/null || true
systemctl disable turntable-web 2>/dev/null || true

# Remove service files
echo "Removing systemd services..."
rm -f /etc/systemd/system/turntable-stream.service
rm -f /etc/systemd/system/turntable-web.service
systemctl daemon-reload

# Remove directories
echo "Removing installed files..."
rm -rf "$INSTALL_DIR"
rm -rf "$DOC_DIR"

# Ask about config
if [ -d "$CONFIG_DIR" ]; then
    echo
    read -p "Remove configuration directory? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo "Configuration removed"
    else
        echo -e "${YELLOW}Configuration preserved at: $CONFIG_DIR${NC}"
    fi
fi

echo
echo -e "${GREEN}Uninstall complete!${NC}"
echo

