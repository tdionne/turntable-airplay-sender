# Auto-Play Detection Feature

Automatically start playing on Sonos when the turntable needle is dropped on a record.

## How It Works

### 1. Audio Level Monitoring
- Continuously monitors incoming audio from the turntable
- Calculates RMS (Root Mean Square) level of audio chunks
- Compares against configured threshold

### 2. Needle Detection
```
Needle Up:    Audio level < threshold (silence/hum)
Needle Down:  Audio level > threshold (music/groove noise)
```

### 3. Circular Buffer (10 seconds)
- Always keeps last 10 seconds of encoded MP3 data in memory
- When needle detected, we have the audio that just happened
- Allows "rewinding" to capture the start of the track

### 4. Auto-Play Trigger
```
1. Needle drops on record
2. Audio starts playing (0:00)
3. Detection triggers at ~2 seconds (0:02)
4. System auto-starts Sonos
5. Sonos connects and buffers (~2 more seconds, 0:04)
6. Playback starts WITH buffered audio from 0:00
7. No music is lost! ✅
```

## Configuration

```yaml
auto_play:
  enabled: true
  default_speaker: "Living Room"
  audio_threshold: 500          # Tune for your turntable
  trigger_delay: 2.0             # Avoid false triggers
  buffer_seconds: 10             # Capture track start
  auto_stop: false               # Optional: stop when record ends
  silence_duration: 30           # Seconds of silence = record ended
```

## Implementation Architecture

### Buffer Management
```python
from collections import deque

# Circular buffer: last N seconds of MP3 data
buffer = deque(maxlen=buffer_chunks)

# Always add new MP3 chunks to buffer
def on_mp3_chunk(chunk):
    buffer.append(chunk)
    
# When auto-play triggers
def send_buffered_start():
    # Send all buffered chunks first
    for chunk in buffer:
        send_to_client(chunk)
    # Then continue with live stream
    send_live_stream()
```

### Audio Level Detection
```python
import numpy as np

def calculate_rms(audio_pcm):
    """Calculate RMS level of audio chunk."""
    samples = np.frombuffer(audio_pcm, dtype=np.int16)
    rms = np.sqrt(np.mean(samples**2))
    return rms

# Monitor continuously
if rms > threshold:
    above_threshold_duration += chunk_duration
    if above_threshold_duration >= trigger_delay:
        trigger_auto_play()
```

### Auto-Play Integration
```python
import soco

def trigger_auto_play():
    """Auto-start playback on default speaker."""
    speaker = find_speaker(default_speaker_name)
    
    # Mark next connection should get buffered start
    enable_buffer_replay = True
    
    # Start playback
    speaker.stop()
    speaker.clear_queue()
    speaker.play_uri(stream_url, title="Turntable")
    
    logger.info(f"🎵 Auto-play triggered on {speaker.player_name}")
```

## Tuning the Threshold

### Find the Right Value

**Too Low (sensitive):**
- Triggers on electrical hum
- Triggers on very quiet passages
- False positives

**Too High (insensitive):**
- Doesn't trigger on quiet music
- Misses needle drop
- False negatives

### Calibration Process

1. **Measure silence level:**
   ```bash
   # Needle up, turntable spinning
   # Check logs for RMS value
   # Example: RMS=50
   ```

2. **Measure music level:**
   ```bash
   # Needle on record, music playing
   # Check logs for RMS value  
   # Example: RMS=3000
   ```

3. **Set threshold between them:**
   ```yaml
   audio_threshold: 500  # Well above 50, well below 3000
   ```

### Testing

```bash
# Enable debug logging
logging:
  level: DEBUG

# Watch the logs
tail -f /opt/turntable-streaming/turntable.log

# You'll see:
# DEBUG - Audio RMS: 45 (below threshold)
# DEBUG - Audio RMS: 52 (below threshold)
# INFO - 🎵 Needle detected! RMS: 2850
# INFO - Auto-play triggered on Living Room
```

## Benefits

✅ **No Lost Audio** - 10 second buffer captures track start  
✅ **Seamless Experience** - Just drop the needle and music plays  
✅ **Smart Detection** - Trigger delay prevents false starts  
✅ **Configurable** - Tune threshold for your setup  
✅ **Manual Override** - Can still control via app/web interface  

## Limitations

⚠️ **Very Quiet Music** - Might not trigger if music is too soft  
⚠️ **Electrical Noise** - Turntable hum might cause false triggers  
⚠️ **Threshold Tuning** - Requires initial setup for your hardware  

## Status: In Development

This feature is planned but not yet implemented in `stream_server_v2.py`.

**To implement:**
1. Add circular buffer for MP3 chunks
2. Add RMS calculation in audio capture thread
3. Add auto-play trigger logic
4. Add buffer replay when Sonos connects
5. Add configuration loading from YAML

**Would you like this feature?** Let us know!

## Alternative: Simple Auto-Play (No Buffer)

A simpler version without buffering:
- Detect needle drop
- Auto-start Sonos
- Accept that first few seconds might be lost
- Much simpler to implement
- Still useful for most use cases

**Trade-off:** Lose ~4-5 seconds vs. complex buffering code

Your choice! 🎵

