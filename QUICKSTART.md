# Quick Start Guide

Get your turntable streaming to Sonos in 10 minutes!

## Prerequisites

- Raspberry Pi (3B+ or newer) with Raspberry Pi OS installed
- USB turntable connected to Raspberry Pi
- Sonos speaker with AirPlay 2 support
- Both devices on the same WiFi network

## 5-Step Setup

### Step 1: Run Setup Script (5 min)

```bash
cd turntable-airplay-sender
chmod +x setup.sh
./setup.sh
```

This will:
- Install all system dependencies
- Set up Python environment
- Configure audio permissions
- Create default config file

⚠️ **Important:** Log out and back in after setup for audio permissions to take effect!

### Step 2: Find Your Turntable (30 sec)

```bash
python3 main.py --list-devices
```

Example output:
```
📻 Available Audio Input Devices:

  [0] bcm2835 Headphones
      Channels: 2, Sample Rate: 48000 Hz

  [1] USB Audio Device
      Channels: 2, Sample Rate: 44100 Hz

  [2] USB PnP Sound Device
      Channels: 2, Sample Rate: 44100 Hz
```

Note the index number of your turntable (probably 1 or 2).

### Step 3: Find Your Sonos (1 min)

```bash
python3 main.py --discover
```

Example output:
```
🔍 Discovering AirPlay devices...

Found 2 AirPlay device(s):

  📱 Living Room Sonos
     Address: 192.168.1.100:7000
     Model: Sonos One

  📱 Kitchen Sonos
     Address: 192.168.1.101:7000
     Model: Sonos Play:5
```

Note the exact name of your target speaker.

### Step 4: Configure (1 min)

Edit `config.yaml`:

```bash
nano config.yaml
```

Update these two lines:
```yaml
audio_input:
  device_index: 1  # Change to your turntable's index

airplay_output:
  device_name: "Living Room Sonos"  # Change to your Sonos name
```

Save and exit (Ctrl+X, Y, Enter).

### Step 5: Start Streaming! (30 sec)

```bash
python3 main.py
```

You should see:
```
✅ Streaming started! Press CTRL+C to stop.
   Input: USB Turntable (44100Hz, 2ch)
   Output: Living Room Sonos via AirPlay 2
```

🎉 **That's it!** Your turntable is now streaming to Sonos!

## Quick Commands

```bash
# Stream to specific device (override config)
python3 main.py --device "Living Room Sonos"

# List audio devices
python3 main.py --list-devices

# Discover AirPlay devices
python3 main.py --discover

# Test audio capture only (no streaming)
python3 main.py test

# Enable verbose logging
python3 main.py --device "Sonos" --verbose

# Stop streaming
Press CTRL+C
```

## Run on Startup (Optional)

To automatically start streaming when Raspberry Pi boots:

```bash
sudo ./install-service.sh
sudo systemctl start turntable-airplay

# Check it's running
sudo systemctl status turntable-airplay
```

## Common Issues

### "Device not found"
- Ensure Sonos and Raspberry Pi on same network
- Check device name is exact (case-sensitive)
- Try `--discover` again

### "No audio"
- Verify turntable is powered on
- Check device_index in config.yaml
- Test with: `arecord -D plughw:1,0 -d 5 test.wav`

### "Permission denied"
- Log out and back in after setup
- Verify: `groups` should include "audio"

### "Crackling audio"
- Edit config.yaml: increase `chunk_size` to 2048
- Use wired Ethernet instead of WiFi
- Check power supply is adequate (2.5A+)

## Latency Note

AirPlay 2 has ~2 seconds of latency. This is normal and intentional for:
- Multi-room synchronization
- Network buffering
- Quality assurance

This is perfect for casual listening but **not suitable for DJ monitoring**. For that, use direct audio output from your mixer.

## Next Steps

- Read [INSTALLATION.md](INSTALLATION.md) for detailed setup
- Read [README.md](README.md) for full documentation
- Read [TECHNICAL.md](TECHNICAL.md) for how it works
- Adjust volume in Sonos app
- Group multiple Sonos speakers for multi-room audio
- Install as service for auto-start

## Getting Help

Still having trouble? Check the logs:

```bash
# If running manually
python3 main.py --device "Sonos" --verbose

# If running as service
sudo journalctl -u turntable-airplay -f
```

## Enjoy Your Music! 🎵

Your turntable is now wireless! Place your Raspberry Pi near your turntable, and enjoy your vinyl collection throughout your home via Sonos.

