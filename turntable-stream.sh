#!/bin/bash
#
# Turntable HTTP Streaming Server
# Streams USB turntable audio as HTTP/MP3 for Sonos
#

set -e

# Configuration
DEVICE="${ALSA_DEVICE:-plughw:2,0}"
PORT="${STREAM_PORT:-8000}"
SAMPLE_RATE="48000"
BITRATE="320k"

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear
echo -e "${GREEN}=========================================="
echo "🎵 Turntable Streaming Server"
echo -e "==========================================${NC}"
echo ""
echo -e "${CYAN}Audio Source:${NC} $DEVICE"
echo -e "${CYAN}Stream URL:${NC}   http://${LOCAL_IP}:${PORT}/turntable.mp3"
echo -e "${CYAN}Quality:${NC}      MP3 $BITRATE, $SAMPLE_RATE Hz, Stereo"
echo ""
echo -e "${YELLOW}┌─────────────────────────────────────────────┐"
echo "│  HOW TO PLAY ON SONOS (One-Time Setup)   │"
echo "└─────────────────────────────────────────────┘${NC}"
echo ""
echo "1. Open the Sonos app on your phone/tablet"
echo "2. Go to: Settings → Services & Voice → Add a Service"
echo "3. Search for 'TuneIn' and add it (if not already added)"
echo "4. Go to: Browse → TuneIn → My Radio Stations"
echo "5. Tap the ⚙️ settings icon → Add New Radio Station"
echo "6. Enter:"
echo -e "   Name: ${GREEN}Turntable${NC}"
echo -e "   URL:  ${GREEN}http://${LOCAL_IP}:${PORT}/turntable.mp3${NC}"
echo "7. Save and select 'Turntable' to play!"
echo ""
echo -e "${YELLOW}Note: You only need to add the URL once!${NC}"
echo -e "${YELLOW}After that, just start this script and play the saved station.${NC}"
echo ""
echo -e "${GREEN}Starting stream...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""
echo "─────────────────────────────────────────────"
echo ""

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg not found${NC}"
    echo "Install with: sudo apt-get install ffmpeg"
    exit 1
fi

# Start streaming with FFmpeg
# -re: Read input at native frame rate (prevents buffering entire file)
# -f alsa: ALSA input format
# -thread_queue_size: Increase buffer to prevent frame drops
ffmpeg -hide_banner -loglevel warning \
       -thread_queue_size 512 \
       -f alsa \
       -i "$DEVICE" \
       -acodec libmp3lame \
       -ab "$BITRATE" \
       -ac 2 \
       -ar "$SAMPLE_RATE" \
       -f mp3 \
       -listen 1 \
       -content_type audio/mpeg \
       "http://0.0.0.0:${PORT}/turntable.mp3" 2>&1 | \
       grep -v "Estimating duration" | \
       while read line; do
           echo "[$(date +%H:%M:%S)] $line"
       done

