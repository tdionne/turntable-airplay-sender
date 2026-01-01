#!/bin/bash
#
# Simple HTTP streaming from USB turntable
# Stream can be played on Sonos via URL
#

DEVICE="plughw:2,0"
PORT="8000"
SAMPLE_RATE="48000"

echo "=========================================="
echo "Turntable HTTP Streaming Server"
echo "=========================================="
echo ""
echo "Capturing from: $DEVICE"
echo "Streaming on: http://$(hostname -I | awk '{print $1}'):$PORT/turntable.mp3"
echo ""
echo "To play on Sonos:"
echo "1. Open Sonos app"
echo "2. Go to Browse > TuneIn"
echo "3. Add custom station with URL above"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Use FFmpeg to capture and stream
ffmpeg -f alsa \
       -i $DEVICE \
       -acodec libmp3lame \
       -ab 320k \
       -ac 2 \
       -ar $SAMPLE_RATE \
       -f mp3 \
       -listen 1 \
       http://0.0.0.0:$PORT/turntable.mp3

