# Technical Documentation

Deep dive into how Turntable AirPlay Sender works.

## Architecture

```
┌─────────────────┐
│  USB Turntable  │
└────────┬────────┘
         │ USB Audio
         ▼
┌─────────────────┐
│  Audio Capture  │  (audio_capture.py)
│   (PyAudio)     │
└────────┬────────┘
         │ PCM Audio Stream
         ▼
┌─────────────────┐
│ Audio Processing│  (optional normalization/gain)
└────────┬────────┘
         │ Processed PCM
         ▼
┌─────────────────┐
│  AirPlay Sender │  (airplay_sender.py)
│   RTP/RTSP      │
└────────┬────────┘
         │ Network (AirPlay 2)
         ▼
┌─────────────────┐
│  Sonos Speaker  │
└─────────────────┘
```

## Components

### 1. Audio Capture (`audio_capture.py`)

**Purpose:** Capture real-time audio from USB turntable

**Technology:**
- PyAudio (PortAudio wrapper)
- ALSA backend (Linux audio)
- Threading for non-blocking capture

**Flow:**
1. Initialize PyAudio with device parameters
2. Open input stream from USB device
3. Capture audio in chunks (frames)
4. Optional: Apply processing (normalization, gain)
5. Queue audio data for transmission
6. Handle buffer overflows gracefully

**Key Features:**
- Device enumeration and selection
- Configurable sample rate, channels, bit depth
- Audio processing pipeline
- Queue-based buffering
- Context manager support

**Latency Considerations:**
- Chunk size: Smaller = lower latency, higher CPU
- Default 1024 frames ≈ 23ms @ 44.1kHz
- Buffer size impacts stability vs latency

### 2. Device Discovery (`device_discovery.py`)

**Purpose:** Find AirPlay devices on local network

**Technology:**
- Zeroconf/Bonjour (mDNS/DNS-SD)
- Service discovery for `_airplay._tcp` and `_raop._tcp`

**Flow:**
1. Initialize Zeroconf browser
2. Listen for mDNS announcements
3. Parse service records (SRV, TXT)
4. Extract device info (name, IP, port, capabilities)
5. Filter for AirPlay 2 capable devices

**Service Types:**
- `_airplay._tcp.local.` - Modern AirPlay devices
- `_raop._tcp.local.` - Remote Audio Output Protocol (older)

**Properties Retrieved:**
- Device name and model
- IP address and port
- Feature flags (AirPlay 2 support)
- Additional metadata

### 3. AirPlay Sender (`airplay_sender.py`)

**Purpose:** Stream audio to AirPlay devices

**Technology:**
- RTSP (Real Time Streaming Protocol)
- RTP (Real-time Transport Protocol)
- TCP sockets for reliable delivery

**Protocol Stack:**

```
Application Layer:  Audio PCM Data
-----------------------------------
Transport Layer:    RTP Packets
-----------------------------------
Session Layer:      RTSP Control
-----------------------------------
Network Layer:      TCP/IP
```

**RTSP Sequence:**

1. **ANNOUNCE:** Declare stream format (SDP)
2. **SETUP:** Negotiate transport parameters
3. **RECORD:** Start receiving audio
4. **[Streaming]:** Send RTP packets
5. **TEARDOWN:** End session

**RTP Packet Format:**
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|X|  CC   |M|     PT      |       Sequence Number         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Timestamp                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Synchronization Source (SSRC) identifier            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Payload Data                         |
|                              ...                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**Streaming Loop:**
1. Dequeue audio chunk
2. Create RTP header
3. Append PCM payload
4. Send via TCP socket
5. Update sequence and timestamp
6. Handle backpressure

**Clock Synchronization:**
- RTP timestamp tracks audio playback position
- Calculated from sample rate and frame count
- Receiver uses for jitter buffer and sync

### 4. Main Application (`main.py`)

**Purpose:** CLI interface and coordination

**Technology:**
- Click (CLI framework)
- PyYAML (configuration)
- Colorlog (logging)
- Threading/signals (lifecycle)

**Command Structure:**
- `--list-devices` - Enumerate audio inputs
- `--discover` - Find AirPlay devices
- `--device NAME` - Start streaming
- `test` - Test audio capture only

**Main Loop:**
1. Parse arguments and config
2. Setup logging
3. Discover target device
4. Initialize audio capture
5. Initialize AirPlay sender
6. Connect and start streaming
7. Monitor and log statistics
8. Handle graceful shutdown

## Audio Pipeline

### Sample Rates

Common rates:
- **44100 Hz** - CD quality (recommended)
- **48000 Hz** - Professional audio
- **96000 Hz** - Hi-res audio (higher CPU)

### Bit Depths

- **16-bit** - Standard quality (recommended)
- **24-bit** - Studio quality
- **32-bit** - Maximum precision

### Channels

- **2** - Stereo (turntables are stereo)
- **1** - Mono (not typical for turntables)

### Buffering

**Capture Buffer:**
- Size: `chunk_size` frames
- Duration: `chunk_size / sample_rate` seconds
- Trade-off: latency vs stability

**Transmission Queue:**
- Size: 100-200 packets
- Absorbs network jitter
- Prevents audio dropout

## Network Protocol Details

### AirPlay 2 Protocol

AirPlay 2 uses several protocols:

1. **mDNS/Bonjour** - Device discovery
2. **RTSP** - Session control
3. **RTP** - Audio streaming
4. **HTTP** - Additional control/metadata
5. **Encryption** - FairPlay DRM (optional)

### Simplified Implementation

This implementation uses a simplified AirPlay approach:

- **No encryption** - Works with compatible devices
- **TCP transport** - More reliable than UDP
- **Direct RTP** - Bypasses some AirPlay complexity
- **L16 codec** - Uncompressed PCM audio

**Limitations:**
- May not work with all AirPlay devices
- No encryption or authentication
- No cover art or metadata
- No multi-room sync beyond Sonos grouping

### Enhanced Implementation Options

For production use, consider:

1. **Full AirPlay Stack:**
   - Use `shairport-sync` or `airplay2-receiver`
   - Implement proper authentication
   - Support encrypted streams

2. **Alternative Protocols:**
   - **Icecast/Shoutcast** - HTTP streaming
   - **RTMP** - Flash Media Server
   - **WebRTC** - Modern real-time streaming

3. **Commercial Solutions:**
   - **Rogue Amoeba Airfoil** - Mature AirPlay sender
   - **AirParrot** - Multi-platform streaming

## Performance Optimization

### CPU Usage

**Factors:**
- Sample rate (higher = more CPU)
- Chunk size (smaller = more processing overhead)
- Audio processing (normalization, gain)
- Network encoding

**Optimization:**
- Use hardware that supports your sample rate
- Disable unnecessary processing
- Use optimal chunk size (1024-2048)
- Ensure good power supply

### Memory Usage

**Components:**
- Audio buffers (~100 KB for queues)
- Python runtime (~50 MB)
- Libraries (PyAudio, etc.)

**Total:** ~100 MB typical

### Network Bandwidth

**Calculation:**
```
Bitrate = sample_rate × channels × bit_depth
Example: 44100 Hz × 2 ch × 16 bit = 1,411,200 bps ≈ 1.4 Mbps
```

**Overhead:**
- RTP headers: ~2%
- TCP/IP headers: ~5%
- **Total:** ~1.5 Mbps

### Latency Budget

**Sources of latency:**
1. Audio capture: 23ms (chunk_size=1024)
2. Processing: <1ms
3. Network transmission: 10-50ms
4. AirPlay buffering: 2000ms (protocol requirement)
5. Sonos processing: 50-100ms

**Total:** ~2.1-2.2 seconds (inherent to AirPlay 2)

**Note:** AirPlay 2 is designed for multi-room sync, not low-latency monitoring. For DJ monitoring, use direct audio output.

## Security Considerations

### Network Security

**Current implementation:**
- No encryption
- No authentication
- Local network only

**Recommendations:**
1. Use trusted local network
2. Enable firewall
3. Isolate IoT devices (VLAN)
4. Monitor network traffic

### System Security

**Service runs as:**
- User: `pi` (or configured user)
- Group: `audio`

**Permissions needed:**
- Audio device access
- Network sockets
- File read (config)

**Hardening:**
- NoNewPrivileges in systemd
- PrivateTmp enabled
- Run as non-root user
- Limit network interfaces

## Debugging

### Enable Verbose Logging

```bash
python3 main.py --device "Sonos" --verbose
```

### Check Audio Capture

```bash
# List ALSA devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f cd -d 5 test.wav

# Analyze audio
ffprobe test.wav
```

### Monitor Network Traffic

```bash
# Install tcpdump
sudo apt-get install tcpdump

# Capture AirPlay traffic
sudo tcpdump -i any port 7000 -w airplay.pcap

# Analyze with Wireshark
wireshark airplay.pcap
```

### System Resources

```bash
# CPU per process
top -p $(pgrep -f main.py)

# Memory usage
ps aux | grep main.py

# Network connections
netstat -tnp | grep python3
```

## Future Enhancements

### Planned Features

1. **Web Interface**
   - Start/stop streaming
   - Device selection
   - Volume control
   - Statistics dashboard

2. **Audio Features**
   - EQ (equalizer)
   - Compressor/limiter
   - Noise gate
   - Multiple input sources

3. **Network Features**
   - Multi-device streaming
   - Stream recording
   - Shoutcast/Icecast compatibility
   - Bluetooth input support

4. **Integration**
   - Home Assistant plugin
   - REST API
   - MQTT support
   - Webhook notifications

### Contributing

Areas for contribution:
- Full AirPlay 2 protocol implementation
- Better error handling and recovery
- Additional audio codecs (AAC, ALAC)
- Cross-platform support
- Performance profiling
- Automated testing

## References

- [AirPlay Protocol](https://nto.github.io/AirPlay.html)
- [RTSP RFC 2326](https://tools.ietf.org/html/rfc2326)
- [RTP RFC 3550](https://tools.ietf.org/html/rfc3550)
- [PyAudio Documentation](http://people.csail.mit.edu/hubert/pyaudio/)
- [ALSA Documentation](https://www.alsa-project.org/)

