# Turntable AirPlay Sender

Stream audio from your USB turntable to Sonos speakers via AirPlay 2 on Raspberry Pi.

## Features

- Real-time audio capture from USB turntable
- AirPlay 2 streaming to Sonos systems
- Low-latency audio processing
- Automatic device discovery
- CLI interface for easy control

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- USB turntable (any USB audio device)
- Sonos speakers with AirPlay 2 support
- Network connection

## Software Requirements

- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+
- ALSA/PulseAudio
- Required Python packages (see requirements.txt)

## Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/tdionne/turntable-airplay-sender.git
cd turntable-airplay-sender

# Run the install script
sudo ./install.sh

# Repository can now be deleted!
cd ..
rm -rf turntable-airplay-sender
```

This installs everything to `/opt/turntable-streaming` and sets up the systemd service.

### Manual Installation

If you prefer to run from the cloned directory:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    python3-pip python3-dev python3-venv \
    libasound2-dev portaudio19-dev \
    libavahi-compat-libdnssd-dev \
    libssl-dev libffi-dev ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp config.example.yaml config.yaml
nano config.yaml
```

## Usage

### Start the Stream Server

**If installed with install.sh:**
```bash
# Start service
sudo systemctl start turntable-stream

# Enable auto-start on boot
sudo systemctl enable turntable-stream

# Check status
sudo systemctl status turntable-stream
```

**If running manually:**
```bash
source venv/bin/activate
python3 stream_server_v2.py
```

### Play on Sonos

**Direct control (command line):**
```bash
python3 play_on_sonos.py "Living Room"
```

**Web interface (for family):**
```bash
python3 web_control.py
# Open http://YOUR_PI_IP:8080 in browser
```

**Sonos app (easiest for family):**
1. Add turntable playlist to Sonos Music Library (see FAMILY_INSTRUCTIONS.md)
2. Browse → Music Library → Playlists → Turntable
3. Play!

## Configuration

Edit `config.yaml` to customize:

- Input device (USB turntable)
- Target AirPlay device
- Audio quality settings
- Buffer sizes for latency tuning

## Troubleshooting

### No Audio Input Detected

```bash
# Check USB devices
lsusb

# Check ALSA devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f cd test.wav
```

### AirPlay Connection Issues

- Ensure Raspberry Pi and Sonos are on the same network
- Check firewall settings
- Verify Sonos supports AirPlay 2 (check Sonos app)

### Audio Quality/Latency Issues

- Adjust buffer sizes in config.yaml
- Ensure Raspberry Pi has adequate power supply
- Check CPU usage: `htop`

## Project Structure

```
turntable-airplay-sender/
├── stream_server_v2.py        # Main HTTP streaming server (START HERE)
├── audio_capture_alsa.py      # ALSA audio capture from USB turntable
├── play_on_sonos.py           # Direct Sonos control via SoCo
├── web_control.py             # Web interface for family
├── create_playlist.py         # Generate .m3u playlist file
├── device_discovery.py        # Discover AirPlay devices on network
├── turntable-stream.service   # Systemd service for auto-start
├── setup.sh                   # Initial setup script
├── install-service.sh         # Install as system service
├── requirements.txt           # Python dependencies
├── config.example.yaml        # Configuration template
└── README.md                  # This file
```

## Main Components

**For Daily Use:**
- `stream_server_v2.py` - The main server that captures and streams audio
- `play_on_sonos.py` - Command-line tool to play on specific Sonos speakers
- `web_control.py` - Web interface for family members

**For Setup:**
- `setup.sh` - Run once to install dependencies
- `create_playlist.py` - Generate playlist for Sonos Music Library
- `install-service.sh` - Install as auto-starting service

## License

MIT License - See LICENSE file for details

## Credits

Built using:
- PyAudio for audio capture
- pyatv/airplay2 for AirPlay streaming
- zeroconf for device discovery

