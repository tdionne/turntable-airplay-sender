# Installation Guide

Complete installation guide for Turntable AirPlay Sender on Raspberry Pi.

## Quick Start

```bash
# Clone or download the repository
cd turntable-airplay-sender

# Run setup script
chmod +x setup.sh
./setup.sh

# Configure
nano config.yaml

# Discover devices
python3 main.py --discover

# Start streaming
python3 main.py --device "Your Sonos Name"
```

## Detailed Installation

### 1. Prepare Raspberry Pi

#### Hardware Setup

1. Connect USB turntable to Raspberry Pi USB port
2. Connect Raspberry Pi to your network (WiFi or Ethernet)
3. Ensure Raspberry Pi has a good power supply (2.5A+ recommended)

#### Verify USB Turntable

```bash
# List USB devices
lsusb

# List audio input devices
arecord -l

# You should see your turntable listed as a USB audio device
```

### 2. Install System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    libasound2-dev \
    portaudio19-dev \
    libavahi-compat-libdnssd-dev \
    libssl-dev \
    libffi-dev \
    ffmpeg \
    git

# Add your user to the audio group
sudo usermod -a -G audio $USER

# Log out and back in for group changes to take effect
```

### 3. Install Python Application

```bash
# Navigate to installation directory
cd turntable-airplay-sender

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Application

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

#### Key Configuration Items

**Audio Input:**
- Find your turntable device index: `python3 main.py --list-devices`
- Set `audio_input.device_index` to your turntable's index
- Adjust sample rate if needed (44100 is standard)

**AirPlay Output:**
- Find your Sonos device: `python3 main.py --discover`
- Set `airplay_output.device_name` to your Sonos speaker name

**Audio Processing:**
- Adjust `volume_gain` if audio is too quiet/loud (1.0 = no change)
- Enable `normalize` for automatic volume leveling

### 5. Test Installation

#### Test Audio Capture

```bash
# Test recording from turntable
arecord -D plughw:CARD=Device,DEV=0 -f cd -d 5 test.wav

# Play back to verify
aplay test.wav
```

#### Test Application

```bash
# List audio devices
python3 main.py --list-devices

# Discover AirPlay devices
python3 main.py --discover

# Test audio capture (no streaming)
python3 main.py test

# Test full streaming
python3 main.py --device "Living Room Sonos"
```

### 6. Install as System Service (Optional)

For automatic startup on boot:

```bash
# Install service
sudo ./install-service.sh

# Start service
sudo systemctl start turntable-airplay

# Check status
sudo systemctl status turntable-airplay

# View logs
sudo journalctl -u turntable-airplay -f

# Stop service
sudo systemctl stop turntable-airplay
```

## Troubleshooting

### No Audio Input Detected

**Problem:** Turntable not showing up in device list

**Solutions:**
1. Check USB connection: `lsusb`
2. Check ALSA devices: `arecord -l`
3. Try different USB port
4. Verify power supply is adequate
5. Check `dmesg | tail` for USB errors

### Cannot Connect to Sonos

**Problem:** AirPlay device not found or connection fails

**Solutions:**
1. Ensure Raspberry Pi and Sonos on same network
2. Verify Sonos supports AirPlay 2 (check in Sonos app)
3. Check firewall: `sudo ufw status`
4. Try rebooting Sonos speaker
5. Increase discovery timeout in config.yaml
6. Check network connectivity: `ping YOUR_SONOS_IP`

### Audio Quality Issues

**Problem:** Crackling, dropouts, or poor audio quality

**Solutions:**
1. **Increase buffer size:** Edit `config.yaml`, set `chunk_size` to 2048 or 4096
2. **Check CPU usage:** Run `htop` - if high, close other applications
3. **Improve power supply:** Weak power can cause audio issues
4. **Use wired network:** WiFi can introduce latency
5. **Disable WiFi power management:**
   ```bash
   sudo iwconfig wlan0 power off
   ```

### High Latency

**Problem:** Noticeable delay between turntable and speakers

**Solutions:**
1. Reduce chunk_size in config.yaml (try 512)
2. Use wired Ethernet instead of WiFi
3. Ensure no other network-intensive applications running
4. AirPlay 2 has inherent ~2 second latency - this is normal

### Service Won't Start

**Problem:** systemd service fails to start

**Solutions:**
1. Check logs: `sudo journalctl -u turntable-airplay -n 50`
2. Verify config.yaml exists and is valid
3. Check file permissions: `ls -la`
4. Test manually first: `python3 main.py --device "Sonos"`
5. Verify paths in service file: `cat /etc/systemd/system/turntable-airplay.service`

### Permission Errors

**Problem:** Permission denied errors

**Solutions:**
1. Add user to audio group: `sudo usermod -a -G audio $USER`
2. Log out and back in
3. Check file ownership: `ls -la`
4. For service, ensure correct user in service file

## Advanced Configuration

### Automatic USB Device Detection

Edit config.yaml:
```yaml
audio_input:
  device_index: null  # Auto-detect USB audio device
```

### Audio Quality Settings

For high-quality playback:
```yaml
audio_input:
  sample_rate: 48000
  sample_width: 24
  chunk_size: 2048
```

For low-latency:
```yaml
audio_input:
  sample_rate: 44100
  sample_width: 16
  chunk_size: 512
```

### Multiple Sonos Speakers

To stream to multiple speakers, group them in the Sonos app first, then stream to the group.

### Startup on Boot

1. Install as service (see above)
2. Service will auto-start on boot
3. To disable: `sudo systemctl disable turntable-airplay`

## Performance Tips

1. **Use Raspberry Pi 3B+ or newer** - Better CPU and network
2. **Use wired Ethernet** - More stable than WiFi
3. **Dedicated power supply** - 2.5A+ official power supply
4. **Keep system updated** - Regular `apt-get update && apt-get upgrade`
5. **Disable unnecessary services** - Free up resources
6. **Use quality USB cable** - For turntable connection

## Monitoring

### View Real-time Logs

```bash
# If running manually
python3 main.py --device "Sonos" --verbose

# If running as service
sudo journalctl -u turntable-airplay -f
```

### Check System Resources

```bash
# CPU and memory usage
htop

# Network usage
iftop

# Temperature (important for Raspberry Pi)
vcgencmd measure_temp
```

## Updating

```bash
# Pull latest changes (if using git)
git pull

# Update Python dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart service if installed
sudo systemctl restart turntable-airplay
```

## Uninstalling

```bash
# Stop and disable service
sudo systemctl stop turntable-airplay
sudo systemctl disable turntable-airplay
sudo rm /etc/systemd/system/turntable-airplay.service
sudo systemctl daemon-reload

# Remove application
cd ..
rm -rf turntable-airplay-sender
```

## Getting Help

If you encounter issues:

1. Check logs for error messages
2. Run with `--verbose` flag for detailed output
3. Verify all installation steps completed
4. Check that hardware is properly connected
5. Test components individually (audio capture, device discovery)

## Additional Resources

- [Raspberry Pi Audio Configuration](https://www.raspberrypi.org/documentation/configuration/audio-config.md)
- [Sonos AirPlay 2 Support](https://support.sonos.com/s/article/3454)
- [ALSA Configuration](https://alsa-project.org/wiki/Main_Page)

