#!/bin/bash
#
# Setup script for Turntable AirPlay Sender on Raspberry Pi
#

set -e

echo "========================================"
echo "Turntable AirPlay Sender - Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo -e "${GREEN}[1/6] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
echo -e "${GREEN}[2/6] Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    libasound2-dev \
    portaudio19-dev \
    libavahi-compat-libdnssd-dev \
    libssl-dev \
    libffi-dev \
    ffmpeg \
    git

# Add user to audio group
echo -e "${GREEN}[3/6] Configuring audio permissions...${NC}"
sudo usermod -a -G audio $USER

# Create virtual environment
echo -e "${GREEN}[4/6] Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment and install Python packages
echo -e "${GREEN}[5/6] Installing Python packages...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create config from example if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo -e "${GREEN}[6/6] Creating configuration file...${NC}"
    cp config.example.yaml config.yaml
    echo -e "${YELLOW}Please edit config.yaml with your settings${NC}"
else
    echo -e "${GREEN}[6/6] Configuration file already exists${NC}"
fi

# List audio devices
echo ""
echo -e "${GREEN}Available audio input devices:${NC}"
python3 main.py --list-devices

echo ""
echo -e "${GREEN}========================================"
echo "Setup complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your device settings"
echo "2. Discover AirPlay devices: python3 main.py --discover"
echo "3. Test streaming: python3 main.py --device 'Your Sonos'"
echo "4. (Optional) Install as service: sudo ./install-service.sh"
echo ""
echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"

