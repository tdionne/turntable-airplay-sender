# Turntable AirPlay Sender

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red.svg)](https://www.raspberrypi.org/)
[![Sonos](https://img.shields.io/badge/Sonos-Multi--Room-green.svg)](https://www.sonos.com/)

**Transform your vinyl collection into a wireless, multi-room listening experience!**

Stream audio from any USB turntable to Sonos speakers using a Raspberry Pi. No subscriptions, no cloud services—just pure analog warmth delivered to your modern wireless speakers.

Perfect for audiophiles and families who want to enjoy vinyl records throughout their home without complicated setups.

---

## 🚀 Quick Start

```bash
# On your Raspberry Pi
git clone https://github.com/tdionne/turntable-airplay-sender.git
cd turntable-airplay-sender
sudo ./install.sh
```

That's it! The streaming server auto-starts on boot. Access the web UI at `http://YOUR_PI_IP:8080`

---

## 📋 Table of Contents

- [Why This Project?](#-why-this-project)
- [Quick Start](#-quick-start)
- [Features](#features)
- [Demo](#demo)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Use Cases](#-use-cases)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Demo

> 🎥 **Coming soon:** Screenshots of the web interface and setup process

In the meantime, here's what you get:
- **Web Control Panel** - Gorgeous, responsive UI to control all your Sonos speakers
- **Live Status Indicators** - See which speakers are playing in real-time
- **Smart Grouping** - Automatically detects and displays grouped speakers
- **Auto-Play Detection** - Just drop the needle and music starts automatically
- **Settings Dashboard** - Configure everything from your browser

---

## ✨ Why This Project?

Ever wanted to play your vinyl collection through your Sonos speakers without buying expensive dedicated hardware? This project turns a $35 Raspberry Pi into a powerful bridge between your turntable and modern wireless speakers.

**What makes it special:**
- ⚡ **Auto-play detection** - Power on your turntable, drop the needle, music starts automatically
- 🎛️ **Web interface** - Control everything from your phone or computer
- 👨‍👩‍👧‍👦 **Family-friendly** - Non-technical users can operate it easily
- 🔓 **No subscriptions** - No TuneIn, Spotify, or cloud services required
- 🛠️ **Fully customizable** - Adjust gain, thresholds, and behavior to your needs

---

## Features

- 🎵 **Real-time audio streaming** from USB turntable to Sonos
- 🔊 **High-quality MP3 encoding** (320kbps, 48kHz stereo)
- 🎚️ **Volume boost** for quiet turntables (configurable gain)
- 🤖 **Auto-play detection** - Drop the needle, playback starts automatically!
- 📱 **Family-friendly** - Shows up in Sonos app Music Library
- 🌐 **Web control interface** for easy speaker selection
- 🔄 **Multi-client support** - Multiple speakers can listen simultaneously
- ⚡ **Auto-start on boot** via systemd service

## Hardware Requirements

**What you need:**
- **Raspberry Pi** (3B+, 4, or 5 recommended) - Acts as the streaming bridge
- **USB turntable** - Any turntable with USB output (Audio-Technica, Denon, Sony, etc.)
  - Also works with traditional turntables using a USB audio interface
- **Sonos speakers** - One or more Sonos speakers (Play:1, Play:5, Beam, Arc, etc.)
  - Must support AirPlay 2 (most modern Sonos devices do)
- **Home network** - Wi-Fi or Ethernet connection for both Pi and Sonos

**Tested configurations:**
- ✅ Raspberry Pi 3B+ with Audio-Technica AT-LP120XUSB
- ✅ Raspberry Pi 4 with various USB turntables
- ✅ Works with Sonos One, Play:5, Beam, and grouped speakers

## Software Requirements

- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+
- ALSA for audio capture
- FFmpeg for encoding
- Dependencies auto-installed via `install.sh`

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

Edit `config.yaml` (or `/opt/turntable-streaming/config.yaml`) to customize:

### Audio Settings
- **Input device**: ALSA device string (e.g., `plughw:2,0`)
- **Sample rate**: 44100 or 48000 Hz
- **Volume gain**: Boost quiet turntables (1.0-3.0, default: 2.0)

### Auto-Play Detection (Optional)
Enable automatic playback when you drop the needle:

```yaml
auto_play:
  enabled: true                    # Enable auto-play
  default_speaker: "Living Room"   # Which Sonos speaker to use
  audio_threshold: 500             # Sensitivity (300-1000)
  trigger_delay: 2.0               # Seconds to wait before triggering
```

**How it works:**
1. Server monitors audio levels in real-time
2. When audio crosses threshold for `trigger_delay` seconds
3. Automatically starts playback on your default Sonos speaker
4. No need to manually start playback!

**Testing auto-play:**
```bash
# Test detection without starting the server
python3 test_autoplay.py
# Drop the needle and watch for trigger
```

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

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

**What this means:**
- ✅ You can use, modify, and distribute this software freely
- ✅ You can use it for commercial purposes
- ⚠️ **If you distribute modified versions, you must:**
  - Share your source code under GPL-3.0
  - Keep the same license
  - Document your changes

This ensures improvements benefit everyone! See the [LICENSE](LICENSE) file for full details.

## 💼 Use Cases

**Perfect for:**
- 🏠 **Home vinyl listening** - Play records in any room with Sonos
- 🎉 **Parties** - Stream to multiple speakers simultaneously
- 👴 **Seniors** - Simple auto-play makes it easy for non-technical users
- 🎧 **Audiophiles** - High-quality 320kbps streaming preserves vinyl warmth
- 🎁 **DIY Gift** - Build one for vinyl-loving friends/family
- 📻 **Podcasters** - Stream any audio source to Sonos
- 🎵 **Music production** - Monitor audio from DAW through Sonos

---

## Contributing

**We'd love your help!** Here's how you can contribute:

- 🐛 **Found a bug?** [Open an issue](https://github.com/tdionne/turntable-airplay-sender/issues/new) with details
- 💡 **Have an idea?** Share your feature request or improvement suggestion
- 🔧 **Want to code?** Fork the repo and submit a pull request
- 📖 **Improve docs?** Documentation improvements are always welcome
- ⭐ **Spread the word** - Star this repo and share with vinyl enthusiasts!

**Development areas that need help:**
- Support for other speaker systems (Bose, HomePod, Chromecast)
- Mobile app for iOS/Android
- Advanced EQ and audio processing
- Better visualization/VU meters
- Automated testing

Join the discussion in [Issues](https://github.com/tdionne/turntable-airplay-sender/issues) or start a [Discussion](https://github.com/tdionne/turntable-airplay-sender/discussions)!

## Credits

Built using:
- [SoCo](https://github.com/SoCo/SoCo) - Python library for Sonos control (MIT)
- [FFmpeg](https://ffmpeg.org/) - Audio encoding (LGPL/GPL)
- [Flask](https://flask.palletsprojects.com/) - Web framework (BSD)
- [pyalsaaudio](https://larsimmisch.github.io/pyalsaaudio/) - ALSA audio capture (PSF)

