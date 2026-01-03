# Testing Auto-Play Detection

## Prerequisites

1. **Install dependencies** (if not already installed):
   ```bash
   cd /opt/turntable-streaming
   source venv/bin/activate
   pip install pyalsaaudio pyyaml
   ```

2. **Create config.yaml** from example:
   ```bash
   cp config.example.yaml config.yaml
   ```

3. **Enable auto-play** in `config.yaml`:
   ```yaml
   auto_play:
     enabled: true
     default_speaker: "Living Room"  # Change to your speaker name
     audio_threshold: 500
     trigger_delay: 2.0
   ```

## Step 1: Test Audio Level Detection

First, test that the server can detect audio from your turntable:

```bash
cd /opt/turntable-streaming
source venv/bin/activate
python3 test_autoplay.py
```

**What to do:**
1. Let it run with turntable silent - should show low RMS levels (~0-100)
2. Drop the needle on a record
3. Watch for "🎵 Audio detected!" message
4. Should trigger after 2 seconds of audio above threshold

**Expected output:**
```
🔇 Quiet: RMS= 45 (threshold=500)
🔇 Quiet: RMS= 52 (threshold=500)

🎵 Audio detected! RMS=1234
   Waiting 2.0s to confirm...
   0.5s / 2.0s - RMS=1456 ████████████████
   1.0s / 2.0s - RMS=1389 █████████████
   1.5s / 2.0s - RMS=1502 ███████████████

✅ TRIGGER! Would start Sonos playback now!
   (RMS level: 1478)
```

**Troubleshooting:**
- **Never triggers**: Threshold too high, try 300 or lower
- **Triggers on silence**: Threshold too low, try 800 or higher
- **Triggers too early**: Increase `trigger_delay` to 3.0 or 4.0
- **No audio detected**: Check ALSA device with `arecord -l`

## Step 2: Test Full Auto-Play with Sonos

Once detection is working, test the full server with auto-play:

```bash
# Stop existing service
sudo systemctl stop turntable-stream

# Run server manually to see logs
cd /opt/turntable-streaming
source venv/bin/activate
python3 stream_server_v2.py
```

**What to do:**
1. Server should start and show "🎵 Auto-play: ENABLED"
2. Drop the needle on a record
3. Watch for auto-play trigger messages
4. Sonos should start playing automatically!

**Expected output:**
```
🎵 Turntable Streaming Server v2
============================================================
📻 Audio Source: plughw:2,0
🔊 Volume Boost: 2.0x
🌐 Stream URL:   http://10.0.0.30:8000/turntable.mp3

🎵 Auto-play:    ENABLED
   Speaker:      Living Room
   Threshold:    500
   Trigger delay: 2.0s

💡 Drop the needle and playback will start automatically!
============================================================

12:34:56 - INFO - 🎤 Starting audio capture from plughw:2,0
12:34:56 - INFO - 🎵 Auto-play: Enabled for speaker 'Living Room'
12:34:56 - INFO - ✅ ALSA device opened: 48000Hz, 2ch, 16-bit
12:34:56 - INFO - ✅ FFmpeg started, encoding to MP3
12:34:58 - INFO - 🌐 HTTP server listening on port 8000

... (drop needle) ...

12:35:10 - INFO - 🎵 Auto-play: Audio detected (RMS=1234), waiting 2.0s...
12:35:12 - INFO - 🎵 Auto-play: Triggering playback!
12:35:12 - INFO - 🎵 Auto-play: Discovering Sonos speakers...
12:35:13 - INFO - 🔊 Auto-play: Starting playback on 'Living Room'
12:35:14 - INFO - ✅ Auto-play: Playback started successfully
12:35:14 - INFO - ✅ Client connected: 10.0.0.64
```

**Troubleshooting:**
- **"Speaker 'X' not found"**: Check speaker name with `python3 play_on_sonos.py`
- **Triggers but no playback**: Check Sonos is on same network
- **Playback stops immediately**: Stream server might have crashed, check logs

## Step 3: Enable Service with Auto-Play

Once everything works, restart the service:

```bash
# Make sure config.yaml is in the right place
sudo cp config.yaml /opt/turntable-streaming/config.yaml

# Restart service
sudo systemctl restart turntable-stream

# Check logs
sudo journalctl -u turntable-stream -f
```

## Tuning the Threshold

The `audio_threshold` value depends on your turntable's output level:

- **Quiet turntable**: Try 200-400
- **Normal turntable**: Try 400-600 (default: 500)
- **Loud turntable**: Try 600-1000

Use `test_autoplay.py` to see your actual RMS levels and adjust accordingly.

## Known Limitations

1. **First ~2 seconds lost**: Simple version doesn't buffer, so you'll miss the very start of the track
2. **No auto-stop**: Playback continues after record ends (stop manually or via Sonos app)
3. **One speaker only**: Auto-play only triggers one speaker (but you can group in Sonos app)

For buffering and auto-stop, see `AUTO_PLAY.md` for the full implementation (Option 1).

