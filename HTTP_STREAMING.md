# HTTP Streaming to Sonos

## Why HTTP Instead of AirPlay?

Modern Sonos speakers use **AirPlay 2**, which is a proprietary Apple protocol. While there are open-source AirPlay 1 implementations (RAOP), Sonos devices **reject AirPlay 1 connections**.

Open-source AirPlay 2 *senders* are extremely rare because:
- Apple's protocol is proprietary and encrypted
- Most open-source tools are for *receiving* AirPlay
- Commercial solutions exist but aren't open source

**HTTP streaming is the most reliable solution** that actually works with Sonos.

## How It Works

```
USB Turntable → ALSA → FFmpeg → HTTP/MP3 Stream → Sonos App → Sonos Speakers
```

The turntable audio is:
1. Captured from USB via ALSA
2. Encoded to MP3 by FFmpeg
3. Served as an HTTP stream
4. Played by Sonos via a saved radio station

## Quick Start

### 1. Start the Stream

```bash
cd /root/turntable-airplay-sender
chmod +x turntable-stream.sh
./turntable-stream.sh
```

The script will display the stream URL (e.g., `http://10.0.0.218:8000/turntable.mp3`)

### 2. Add to Sonos (One-Time Setup)

**Option A: Via TuneIn (Recommended)**

1. Open Sonos app
2. Go to **Settings → Services & Voice**
3. Add **TuneIn** if not already added
4. Go to **Browse → TuneIn → My Radio Stations**
5. Tap **⚙️ Settings** → **Add New Radio Station**
6. Enter:
   - **Name:** Turntable
   - **URL:** `http://YOUR_PI_IP:8000/turntable.mp3`
7. Save

**Option B: Via Sonos Favorites**

1. Open Sonos app
2. Go to **Browse → Radio by TuneIn**
3. Or use **Add to Sonos** feature
4. Add custom URL: `http://YOUR_PI_IP:8000/turntable.mp3`

### 3. Play Your Turntable

1. Put a record on
2. Open Sonos app
3. Select **Turntable** from My Radio Stations
4. Enjoy! 🎵

## Auto-Start on Boot

To have the stream start automatically when your Raspberry Pi boots:

```bash
# Install as systemd service
sudo cp turntable-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable turntable-stream
sudo systemctl start turntable-stream

# Check status
sudo systemctl status turntable-stream

# View logs
sudo journalctl -u turntable-stream -f
```

## Configuration

Edit `turntable-stream.sh` to customize:

```bash
DEVICE="plughw:2,0"      # ALSA device (from arecord -l)
PORT="8000"              # HTTP port
SAMPLE_RATE="48000"      # Sample rate (44100 or 48000)
BITRATE="320k"           # MP3 bitrate (higher = better quality)
```

Or set environment variables:

```bash
ALSA_DEVICE=plughw:2,0 STREAM_PORT=8080 ./turntable-stream.sh
```

## Quality Settings

**High Quality (Recommended):**
```bash
BITRATE="320k"
SAMPLE_RATE="48000"
```

**Medium Quality:**
```bash
BITRATE="192k"
SAMPLE_RATE="44100"
```

**Low Latency (lower quality):**
```bash
BITRATE="128k"
SAMPLE_RATE="44100"
```

## Latency

HTTP streaming has approximately **2-5 seconds** of latency:
- Audio capture: ~50ms
- MP3 encoding: ~100ms
- Network buffering: ~500ms
- Sonos buffering: 1-4 seconds

This is normal for streaming and perfect for casual listening. If you need real-time monitoring, use direct audio output from your DJ mixer.

## Troubleshooting

### Stream won't start

```bash
# Check if port is in use
sudo netstat -tlnp | grep 8000

# Kill existing process
sudo pkill -f turntable-stream.sh

# Check FFmpeg is installed
ffmpeg -version
```

### No audio from turntable

```bash
# Test ALSA capture
arecord -D plughw:2,0 -f cd -d 5 test.wav
aplay test.wav

# Check audio levels
alsamixer
```

### Sonos can't find stream

- Ensure Pi and Sonos are on **same network**
- Check firewall: `sudo ufw status`
- Verify stream is running: `curl http://localhost:8000/turntable.mp3`
- Try the Pi's IP directly in a browser

### Audio quality issues

- Increase bitrate in script (320k is maximum for MP3)
- Check CPU usage: `htop` (encoding shouldn't max out CPU)
- Ensure good power supply to Pi
- Use wired Ethernet instead of WiFi

## Advanced: Multiple Simultaneous Listeners

The HTTP stream supports **multiple simultaneous connections**, so you can:
- Play on multiple Sonos speakers
- Listen on your computer (VLC, browser)
- Use it on other devices

Just add the same URL to multiple players!

## Comparison with AirPlay

| Feature | HTTP Streaming | AirPlay 2 |
|---------|---------------|-----------|
| **Setup** | Add URL once | Automatic discovery |
| **Latency** | 2-5 seconds | 2 seconds |
| **Quality** | MP3 320kbps | ALAC lossless |
| **Compatibility** | Works with Sonos | Sonos AirPlay 2 only |
| **Reliability** | ✅ Very reliable | ❌ Open-source senders don't work |
| **Multi-room** | Via Sonos grouping | Via Sonos grouping |
| **Ease of use** | Select station | Just play |

## Why Not Just Use AirPlay?

We tried! But:
1. ✅ **AirPlay 1 (RAOP)** - Sonos rejects it (requires AirPlay 2)
2. ❌ **AirPlay 2 sender** - No reliable open-source implementation
3. ❌ **Our custom RTP** - Too simplified, doesn't work with real devices

HTTP streaming is the **practical, working solution**.

## Future Improvements

Possible enhancements:
- Web interface for start/stop
- Multiple quality streams (auto-select)
- Metadata injection (now playing info)
- Icecast server for better streaming
- HTTPS support
- Dynamic bitrate adjustment

## Alternative: Icecast Server

For more features (metadata, multiple mount points), you could use Icecast:

```bash
sudo apt-get install icecast2 darkice
```

Then configure DarkIce to capture from your turntable and stream to Icecast. This gives you a more "radio station" like experience with metadata support.

Let me know if you want me to set up the Icecast version!

## Questions?

This approach is simple, reliable, and actually works with Sonos. The one-time URL setup is a small trade-off for having a streaming turntable that works perfectly every time.

Enjoy your wireless vinyl! 🎵

