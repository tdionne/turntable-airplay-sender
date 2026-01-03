# Auto-Play Feature Summary

## What Was Implemented

**Simple Auto-Play Detection (Option 2)** - Detects when you drop the needle and automatically starts Sonos playback.

### How It Works

1. **Audio Monitoring**: Server continuously reads raw PCM audio from ALSA device
2. **RMS Calculation**: Calculates Root Mean Square (RMS) audio level for each chunk
3. **Threshold Detection**: When RMS exceeds configured threshold for specified delay
4. **Sonos Trigger**: Automatically discovers and starts playback on default speaker

### Key Features

✅ **Automatic playback** - Drop needle, music plays  
✅ **Configurable sensitivity** - Adjust threshold for your turntable  
✅ **False-trigger prevention** - Requires sustained audio (trigger_delay)  
✅ **No manual intervention** - Perfect for family members  
✅ **Works with existing setup** - No hardware changes needed  

### Trade-offs (Simple Version)

⚠️ **First ~2 seconds lost** - No buffering, so track start is missed  
⚠️ **No auto-stop** - Playback continues after record ends  
⚠️ **Single speaker** - Only triggers one default speaker  

## Configuration

Edit `config.yaml`:

```yaml
auto_play:
  enabled: true                    # Enable/disable auto-play
  default_speaker: "Living Room"   # Which Sonos speaker to use
  audio_threshold: 500             # RMS threshold (300-1000)
  trigger_delay: 2.0               # Seconds above threshold before trigger
```

## Testing

### Quick Test (Detection Only)
```bash
python3 test_autoplay.py
# Drop needle, watch for trigger
```

### Full Test (With Sonos)
```bash
sudo systemctl stop turntable-stream
python3 stream_server_v2.py
# Drop needle, Sonos should auto-play
```

See `TESTING_AUTOPLAY.md` for detailed testing instructions.

## Files Changed

- **stream_server_v2.py**: Refactored to read raw PCM, calculate RMS, trigger Sonos
- **config.example.yaml**: Already had auto-play settings documented
- **test_autoplay.py**: New test script for detection without full server
- **README.md**: Updated with auto-play documentation
- **TESTING_AUTOPLAY.md**: Comprehensive testing guide
- **AUTO_PLAY.md**: Original design doc (Option 1 with buffering)

## Future Enhancement: Full Version (Option 1)

If you want to eliminate the lost audio at track start, see `AUTO_PLAY.md` for the full implementation with:
- 10-second circular buffer
- Replay from exact needle-drop moment
- Auto-stop on silence detection
- No lost audio

This requires more complex buffer management but provides a seamless experience.

## Next Steps

1. **Pull changes on Pi**: `git pull`
2. **Copy config**: `cp config.example.yaml config.yaml`
3. **Edit config**: Enable auto-play, set speaker name
4. **Test detection**: `python3 test_autoplay.py`
5. **Test full system**: `python3 stream_server_v2.py`
6. **Enable service**: `sudo systemctl restart turntable-stream`

Enjoy automatic turntable playback! 🎵
