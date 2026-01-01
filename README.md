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

### 1. System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install audio dependencies
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libasound2-dev \
    portaudio19-dev \
    libavahi-compat-libdnssd-dev \
    libssl-dev \
    libffi-dev

# Install ffmpeg for audio processing
sudo apt-get install -y ffmpeg
```

### 2. Python Dependencies

```bash
cd /path/to/turntable-airplay-sender
pip3 install -r requirements.txt
```

### 3. Configuration

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit configuration with your settings
nano config.yaml
```

## Usage

### List Available Audio Devices

```bash
python3 main.py --list-devices
```

### List Available AirPlay Devices

```bash
python3 main.py --discover
```

### Start Streaming

```bash
# Stream to specific Sonos device
python3 main.py --device "Living Room Sonos"

# Stream with custom configuration
python3 main.py --config config.yaml
```

### Run as Service

```bash
# Copy systemd service file
sudo cp turntable-airplay.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable turntable-airplay
sudo systemctl start turntable-airplay

# Check status
sudo systemctl status turntable-airplay
```

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

