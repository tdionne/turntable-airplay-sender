#!/bin/bash
#
# Stream turntable via DLNA/UPnP (works with Sonos, no subscription needed)
#

DEVICE="${ALSA_DEVICE:-plughw:2,0}"
PORT="8000"

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "🎵 Turntable DLNA Streaming"
echo "=========================================="
echo ""
echo "Starting HTTP stream..."
echo "URL: http://${LOCAL_IP}:${PORT}/turntable.mp3"
echo ""
echo "To play on Sonos:"
echo "1. Open Sonos app"
echo "2. Go to 'Browse' → 'On this Device' or 'This PC'"
echo "3. Or try Settings → Add Music Library"
echo "4. Or use a browser: http://${LOCAL_IP}:${PORT}/turntable.mp3"
echo ""
echo "Alternative: Use any DLNA/UPnP app to browse streams"
echo "Press Ctrl+C to stop"
echo ""

# Start FFmpeg HTTP server
ffmpeg -hide_banner -loglevel info \
       -f alsa -i "$DEVICE" \
       -acodec libmp3lame \
       -ab 320k \
       -ac 2 \
       -ar 48000 \
       -f mp3 \
       -listen 1 \
       -content_type audio/mpeg \
       "http://0.0.0.0:${PORT}/turntable.mp3"

