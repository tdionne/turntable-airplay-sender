#!/bin/bash
#
# Install Turntable Streaming Server
# Copies files to system locations and sets up service
#

set -e

# Configuration
INSTALL_DIR="/opt/turntable-streaming"
DOC_DIR="/usr/share/doc/turntable-streaming"
VENV_DIR="/opt/turntable-streaming/venv"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================="
echo "Turntable Streaming Server - Install"
echo -e "==========================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root: sudo ./install.sh${NC}"
    exit 1
fi

# Create directories
echo "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$DOC_DIR"

# Copy Python files
echo "Installing application files..."
cp stream_server_v2.py "$INSTALL_DIR/"
cp audio_capture_alsa.py "$INSTALL_DIR/"
cp play_on_sonos.py "$INSTALL_DIR/"
cp web_control.py "$INSTALL_DIR/"
cp create_playlist.py "$INSTALL_DIR/"
cp device_discovery.py "$INSTALL_DIR/"
cp add_to_sonos_favorites.py "$INSTALL_DIR/"
cp test_autoplay.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Copy configuration files
echo "Installing configuration..."
cp config.example.yaml "$INSTALL_DIR/"
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp config.example.yaml "$INSTALL_DIR/config.yaml"
    echo -e "${YELLOW}Created default config: $INSTALL_DIR/config.yaml${NC}"
    echo -e "${YELLOW}Edit this file to enable auto-play and customize settings${NC}"
else
    echo "Config already exists, skipping..."
fi

# Copy documentation
echo "Installing documentation..."
cp README.md QUICKSTART.md INSTALLATION.md TECHNICAL.md "$DOC_DIR/"
cp HTTP_STREAMING.md FAMILY_INSTRUCTIONS.md "$DOC_DIR/"
cp AUTO_PLAY.md AUTOPLAY_SUMMARY.md TESTING_AUTOPLAY.md "$DOC_DIR/"
cp LICENSE "$DOC_DIR/"

# Set permissions
chmod 755 "$INSTALL_DIR"/*.py

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$INSTALL_DIR"

# Create virtual environment
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Install systemd services
echo "Installing systemd services..."

# Streaming service
cat > /etc/systemd/system/turntable-stream.service << EOF
[Unit]
Description=Turntable Streaming Server
After=network.target sound.target

[Service]
Type=simple
User=root
Group=audio
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/stream_server_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Web control service
cat > /etc/systemd/system/turntable-web.service << EOF
[Unit]
Description=Turntable Web Control Interface
After=network.target turntable-stream.service
Wants=turntable-stream.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/web_control.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Nightly restart timer (prevents FFmpeg degradation over long uptimes)
cp turntable-stream-restart.service /etc/systemd/system/
cp turntable-stream-restart.timer /etc/systemd/system/

# Reload systemd
systemctl daemon-reload
systemctl enable turntable-stream-restart.timer
systemctl start turntable-stream-restart.timer

echo
echo -e "${GREEN}=========================================="
echo "Installation Complete!"
echo -e "==========================================${NC}"
echo
echo "Files installed to:"
echo "  Application: $INSTALL_DIR"
echo "  Config:      $INSTALL_DIR/config.yaml"
echo "  Docs:        $DOC_DIR"
echo
echo "Next steps:"
echo "  1. Edit config: sudo nano $INSTALL_DIR/config.yaml"
echo "     - Enable auto-play: set 'enabled: true'"
echo "     - Set speaker name: 'default_speaker: \"Living Room\"'"
echo "     - Adjust volume gain if needed"
echo ""
echo "  2. Enable services:"
echo "     sudo systemctl enable turntable-stream"
echo "     sudo systemctl enable turntable-web"
echo ""
echo "  3. Start services:"
echo "     sudo systemctl start turntable-stream"
echo "     sudo systemctl start turntable-web"
echo ""
echo "  4. Check status:"
echo "     sudo systemctl status turntable-stream"
echo "     sudo systemctl status turntable-web"
echo
echo "Web interface will be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):8080"
echo
echo "Test auto-play detection:"
echo "  Test detection:   $VENV_DIR/bin/python3 $INSTALL_DIR/test_autoplay.py"
echo
echo "Manual commands (if needed):"
echo "  Play on Sonos:    $VENV_DIR/bin/python3 $INSTALL_DIR/play_on_sonos.py 'Speaker Name'"
echo "  Create playlist:  $VENV_DIR/bin/python3 $INSTALL_DIR/create_playlist.py"
echo
echo "Documentation:"
echo "  Quick start:      $DOC_DIR/QUICKSTART.md"
echo "  Auto-play setup:  $DOC_DIR/AUTOPLAY_SUMMARY.md"
echo "  Family guide:     $DOC_DIR/FAMILY_INSTRUCTIONS.md"
echo
echo -e "${YELLOW}You can now safely delete the git repository!${NC}"
echo

