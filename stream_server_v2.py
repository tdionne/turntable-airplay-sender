#!/usr/bin/env python3
"""
HTTP streaming server for turntable audio.
Uses FFmpeg for capture + MP3 encoding, broadcasts to multiple HTTP clients.
Includes auto-play detection based on audio level monitoring.
"""

import subprocess
import threading
import socket
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import queue
import signal
import sys
import time
import numpy as np
import soco
import alsaaudio
import struct
import yaml
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global state
is_running = True
clients = []
ffmpeg_process = None

# Auto-play state
auto_play_enabled = False
auto_play_speaker = None
auto_play_threshold = 500
auto_play_trigger_delay = 2.0
auto_play_reset_on_disconnect = 10.0
auto_play_triggered = False
audio_level_history = []
stream_url = None
last_client_disconnect_time = None


def load_config():
    """Load configuration from config.yaml or config.example.yaml."""
    config_paths = [
        Path('config.yaml'),
        Path('/opt/turntable-streaming/config.yaml'),
        Path('config.example.yaml'),
        Path('/opt/turntable-streaming/config.example.yaml'),
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            logger.info(f"Loading config from: {config_path}")
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
    
    logger.warning("No config file found, using defaults")
    return {}


def calculate_rms(audio_data):
    """
    Calculate RMS (Root Mean Square) level from raw audio data.
    
    Args:
        audio_data: Raw PCM audio bytes (16-bit signed)
    
    Returns:
        RMS level (0-32767 for 16-bit audio)
    """
    # Convert bytes to numpy array of 16-bit signed integers
    samples = np.frombuffer(audio_data, dtype=np.int16)
    
    # Calculate RMS
    if len(samples) == 0:
        return 0
    
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return int(rms)


def trigger_sonos_playback(speaker_name, stream_url):
    """
    Trigger playback on the specified Sonos speaker.
    
    Args:
        speaker_name: Name of the Sonos speaker
        stream_url: URL of the stream to play
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"🎵 Auto-play: Discovering Sonos speakers...")
        
        # Discover Sonos devices
        zones = list(soco.discover())
        
        if not zones:
            logger.error("Auto-play: No Sonos speakers found")
            return False
        
        # Find the target speaker
        target_speaker = None
        for zone in zones:
            if zone.player_name.lower() == speaker_name.lower():
                target_speaker = zone
                break
        
        if not target_speaker:
            logger.error(f"Auto-play: Speaker '{speaker_name}' not found")
            logger.info(f"Available speakers: {', '.join([z.player_name for z in zones])}")
            return False
        
        logger.info(f"🔊 Auto-play: Starting playback on '{target_speaker.player_name}'")
        
        # Play the stream
        target_speaker.play_uri(stream_url, title='Turntable')
        
        logger.info("✅ Auto-play: Playback started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Auto-play error: {e}", exc_info=True)
        return False


class StreamHandler(BaseHTTPRequestHandler):
    """HTTP request handler for audio streaming."""
    
    protocol_version = 'HTTP/1.1'
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"Client {self.client_address[0]}: {format % args}")
    
    def do_HEAD(self):
        """Handle HEAD requests (Sonos checks if stream exists)."""
        if self.path != '/turntable.mp3':
            self.send_error(404, "Stream not found")
            return
        
        self.send_response(200)
        self.send_header('Content-Type', 'audio/mpeg')
        self.send_header('Cache-Control', 'no-cache, no-store')
        self.send_header('Connection', 'close')
        self.send_header('icy-name', 'Turntable')
        self.send_header('icy-genre', 'Vinyl')
        self.send_header('icy-br', '320')
        self.end_headers()
        logger.info(f"HEAD request from {self.client_address[0]}")
    
    def do_GET(self):
        """Handle GET requests for the stream."""
        if self.path != '/turntable.mp3':
            self.send_error(404, "Stream not found. Use: /turntable.mp3")
            return
        
        try:
            # Send HTTP headers
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.send_header('Connection', 'close')
            # ICY metadata headers for Sonos display
            self.send_header('icy-name', 'Turntable')
            self.send_header('icy-genre', 'Vinyl')
            self.send_header('icy-br', '320')
            self.send_header('icy-description', 'Live from USB Turntable')
            self.end_headers()
            
            logger.info(f"✅ Client connected: {self.client_address[0]}")
            
            # Create client-specific queue
            client_queue = queue.Queue(maxsize=200)
            
            # Subscribe this client to broadcasts
            clients.append(client_queue)
            
            try:
                # Stream audio to client
                while is_running:
                    try:
                        # Get MP3 data (with timeout)
                        mp3_data = client_queue.get(timeout=2.0)
                        
                        # Send to client
                        self.wfile.write(mp3_data)
                        
                    except queue.Empty:
                        # No data, continue waiting
                        continue
                    except (BrokenPipeError, ConnectionResetError):
                        logger.info(f"Client disconnected: {self.client_address[0]}")
                        break
                    except Exception as e:
                        logger.error(f"Send error: {e}")
                        break
                    
            finally:
                # Unsubscribe client
                global last_client_disconnect_time
                if client_queue in clients:
                    clients.remove(client_queue)
                logger.info(f"Client removed: {self.client_address[0]}")
                
                # Track when last client disconnects (for auto-play reset)
                if len(clients) == 0:
                    last_client_disconnect_time = time.time()
                    logger.debug("All clients disconnected, tracking for auto-play reset")
                
        except Exception as e:
            logger.error(f"Stream error: {e}")


def ffmpeg_capture_thread(device="plughw:2,0", sample_rate=48000, bitrate="320k", volume_gain=2.0):
    """
    Capture raw PCM from ALSA, detect needle drops, and encode to MP3 via FFmpeg.
    
    Process flow:
    1. Read raw PCM audio from ALSA device using pyalsaaudio
    2. Calculate RMS levels and detect needle drops (if auto-play enabled)
    3. Feed raw PCM to FFmpeg stdin for MP3 encoding
    4. Read MP3 from FFmpeg stdout and broadcast to clients
    
    Args:
        device: ALSA device string (e.g., "plughw:2,0")
        sample_rate: Audio sample rate (Hz)
        bitrate: MP3 encoding bitrate
        volume_gain: Volume multiplier (1.0 = no change, 2.0 = double volume)
    """
    global ffmpeg_process, auto_play_triggered, audio_level_history
    
    logger.info(f"🎤 Starting audio capture from {device}")
    logger.info(f"🔊 Volume gain: {volume_gain}x")
    
    if auto_play_enabled:
        logger.info(f"🎵 Auto-play: Enabled for speaker '{auto_play_speaker}'")
        logger.info(f"🎵 Auto-play: Threshold={auto_play_threshold}, Delay={auto_play_trigger_delay}s, Reset after {auto_play_reset_on_disconnect}s disconnect")
    
    # Open ALSA PCM device for capture
    try:
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            device=device,
            channels=2,
            rate=sample_rate,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=1024
        )
        logger.info(f"✅ ALSA device opened: {sample_rate}Hz, 2ch, 16-bit")
    except Exception as e:
        logger.error(f"Failed to open ALSA device: {e}")
        return
    
    # Start FFmpeg to encode PCM stdin to MP3 stdout
    cmd = [
        'ffmpeg',
        '-f', 's16le',           # Input format: signed 16-bit little-endian PCM
        '-ar', str(sample_rate), # Input sample rate
        '-ac', '2',              # Input channels (stereo)
        '-i', 'pipe:0',          # Read from stdin
        '-af', f'volume={volume_gain}',  # Apply volume gain
        '-acodec', 'libmp3lame',
        '-ab', bitrate,
        '-f', 'mp3',
        'pipe:1'                 # Output to stdout
    ]
    
    try:
        ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=8192
        )
        
        logger.info("✅ FFmpeg started, encoding to MP3")
        
        # Start thread to monitor FFmpeg stderr
        def log_ffmpeg_stderr():
            for line in ffmpeg_process.stderr:
                line_str = line.decode().strip()
                if line_str:
                    logger.debug(f"FFmpeg: {line_str}")
        
        stderr_thread = threading.Thread(target=log_ffmpeg_stderr, daemon=True)
        stderr_thread.start()
        
        # Start thread to read MP3 output from FFmpeg
        def read_ffmpeg_output():
            chunk_size = 8192
            bytes_read = 0
            while is_running and ffmpeg_process and ffmpeg_process.poll() is None:
                try:
                    mp3_data = ffmpeg_process.stdout.read(chunk_size)
                    
                    if not mp3_data:
                        logger.warning("FFmpeg stopped producing data")
                        break
                    
                    bytes_read += len(mp3_data)
                    if bytes_read % (8192 * 100) == 0:  # Log every ~800KB
                        logger.debug(f"Streamed {bytes_read // 1024}KB so far")
                    
                    # Broadcast to all connected clients
                    dead_clients = []
                    for client_queue in clients:
                        try:
                            client_queue.put_nowait(mp3_data)
                        except queue.Full:
                            logger.debug("Client queue full, dropping chunk")
                        except Exception as e:
                            logger.debug(f"Client queue error: {e}")
                            dead_clients.append(client_queue)
                    
                    # Clean up dead clients
                    for client in dead_clients:
                        if client in clients:
                            clients.remove(client)
                            
                except Exception as e:
                    if is_running:
                        logger.error(f"FFmpeg read error: {e}", exc_info=True)
                        time.sleep(0.1)
        
        output_thread = threading.Thread(target=read_ffmpeg_output, daemon=True)
        output_thread.start()
        
        # Main loop: read PCM from ALSA, detect needle drops, feed to FFmpeg
        trigger_time = None
        
        while is_running:
            try:
                # Read PCM audio from ALSA
                length, pcm_data = pcm.read()
                
                if length <= 0:
                    time.sleep(0.001)
                    continue
                
                # Auto-play detection (always monitor if enabled)
                if auto_play_enabled:
                    global auto_play_triggered, last_client_disconnect_time
                    
                    rms_level = calculate_rms(pcm_data)
                    audio_level_history.append((time.time(), rms_level))
                    
                    # Keep only recent history (last 10 seconds)
                    cutoff_time = time.time() - 10.0
                    audio_level_history = [
                        (t, lvl) for t, lvl in audio_level_history if t > cutoff_time
                    ]
                    
                    # Check if we should reset trigger (all clients disconnected for too long)
                    if auto_play_triggered and last_client_disconnect_time is not None:
                        if len(clients) == 0:
                            # No clients connected
                            disconnect_duration = time.time() - last_client_disconnect_time
                            if disconnect_duration >= auto_play_reset_on_disconnect:
                                # Sonos has been disconnected long enough - user switched away
                                logger.info(f"🎵 Auto-play: No clients for {disconnect_duration:.0f}s, resetting (speaker likely switched to TV/stopped)")
                                auto_play_triggered = False
                                last_client_disconnect_time = None
                        else:
                            # Clients reconnected, clear disconnect timer
                            last_client_disconnect_time = None
                    
                    # Check if audio is above threshold
                    if rms_level > auto_play_threshold:
                        # Only trigger if not already triggered
                        if not auto_play_triggered:
                            if trigger_time is None:
                                # Audio just crossed threshold
                                trigger_time = time.time()
                                logger.info(f"🎵 Auto-play: Audio detected (RMS={rms_level}), waiting {auto_play_trigger_delay}s...")
                            else:
                                # Check if we've been above threshold long enough
                                if time.time() - trigger_time >= auto_play_trigger_delay:
                                    logger.info(f"🎵 Auto-play: Triggering playback!")
                                    auto_play_triggered = True
                                    
                                    # Trigger Sonos playback in background thread
                                    def trigger_playback():
                                        trigger_sonos_playback(auto_play_speaker, stream_url)
                                    
                                    threading.Thread(target=trigger_playback, daemon=True).start()
                                    trigger_time = None
                    else:
                        # Audio below threshold - reset trigger timer if we were waiting
                        if trigger_time is not None:
                            logger.debug("Auto-play: Audio dropped below threshold, resetting trigger timer")
                            trigger_time = None
                    
                    # Log RMS level periodically
                    if len(audio_level_history) % 100 == 0:
                        logger.debug(f"Audio RMS: {rms_level} (threshold: {auto_play_threshold})")
                
                # Feed PCM data to FFmpeg
                if ffmpeg_process and ffmpeg_process.poll() is None:
                    try:
                        ffmpeg_process.stdin.write(pcm_data)
                        ffmpeg_process.stdin.flush()
                    except BrokenPipeError:
                        logger.error("FFmpeg stdin closed unexpectedly")
                        break
                else:
                    logger.error("FFmpeg process terminated unexpectedly")
                    break
                    
            except Exception as e:
                if is_running:
                    logger.error(f"Capture error: {e}", exc_info=True)
                    time.sleep(0.1)
                
    except FileNotFoundError:
        logger.error("FFmpeg not found! Install with: sudo apt-get install ffmpeg")
    except Exception as e:
        logger.error(f"Capture thread error: {e}", exc_info=True)
    finally:
        # Clean up
        if ffmpeg_process:
            try:
                ffmpeg_process.stdin.close()
            except:
                pass
            ffmpeg_process.terminate()
            try:
                ffmpeg_process.wait(timeout=5)
            except:
                ffmpeg_process.kill()
        logger.info("Audio capture stopped")


def get_local_ip():
    """Get local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global is_running, ffmpeg_process
    logger.info("\n\nShutting down...")
    is_running = False
    if ffmpeg_process:
        ffmpeg_process.terminate()
    sys.exit(0)


def main():
    """Main server function."""
    global is_running, auto_play_enabled, auto_play_speaker
    global auto_play_threshold, auto_play_trigger_delay, auto_play_reset_on_disconnect, stream_url
    
    # Load configuration
    config = load_config()
    
    # Audio settings
    audio_input = config.get('audio_input', {})
    DEVICE = audio_input.get('alsa_device', 'plughw:2,0')
    SAMPLE_RATE = audio_input.get('sample_rate', 48000)
    
    # Audio processing settings
    audio_processing = config.get('audio_processing', {})
    VOLUME_GAIN = audio_processing.get('volume_gain', 2.0)
    
    # Network settings
    PORT = 8000
    BITRATE = "320k"
    
    # Auto-play settings
    auto_play_config = config.get('auto_play', {})
    auto_play_enabled = auto_play_config.get('enabled', False)
    auto_play_speaker = auto_play_config.get('default_speaker', 'Living Room')
    auto_play_threshold = auto_play_config.get('audio_threshold', 500)
    auto_play_trigger_delay = auto_play_config.get('trigger_delay', 2.0)
    auto_play_reset_on_disconnect = auto_play_config.get('reset_on_disconnect_delay', 10.0)
    
    local_ip = get_local_ip()
    stream_url = f"http://{local_ip}:{PORT}/turntable.mp3"
    
    print("\n" + "=" * 60)
    print("🎵 Turntable Streaming Server v2")
    print("=" * 60)
    print(f"\n📻 Audio Source: {DEVICE}")
    print(f"🔊 Volume Boost: {VOLUME_GAIN}x")
    print(f"🌐 Stream URL:   {stream_url}")
    print(f"📊 Quality:      MP3 {BITRATE}, {SAMPLE_RATE}Hz, Stereo")
    print(f"\n✅ Supports multiple simultaneous listeners")
    print(f"✅ Properly encoded MP3 stream for Sonos")
    
    if auto_play_enabled:
        print(f"\n🎵 Auto-play:    ENABLED")
        print(f"   Speaker:      {auto_play_speaker}")
        print(f"   Threshold:    {auto_play_threshold}")
        print(f"   Trigger delay: {auto_play_trigger_delay}s")
        print(f"   Reset after:  {auto_play_reset_on_disconnect}s disconnect")
        print(f"\n💡 Drop the needle and playback will start automatically!")
        print(f"💡 Stays active while playing - take your time finding records!")
    else:
        print(f"\n💡 To play on Sonos:")
        print(f"   python3 play_on_sonos.py")
        print(f"\n💡 To enable auto-play, edit config.yaml:")
        print(f"   auto_play:")
        print(f"     enabled: true")
    
    print(f"\n💡 To adjust volume, edit config.yaml (volume_gain)")
    print(f"   (1.0 = normal, 2.0 = double, 3.0 = triple)")
    print(f"\n⏹️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start audio capture in background thread
    capture_thread = threading.Thread(
        target=ffmpeg_capture_thread,
        args=(DEVICE, SAMPLE_RATE, BITRATE, VOLUME_GAIN),
        daemon=True
    )
    capture_thread.start()
    
    # Give capture thread a moment to initialize
    time.sleep(2)
    
    # Start HTTP server
    server = HTTPServer(('0.0.0.0', PORT), StreamHandler)
    
    logger.info(f"🌐 HTTP server listening on port {PORT}")
    logger.info("Waiting for clients to connect...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        is_running = False
        server.shutdown()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()

