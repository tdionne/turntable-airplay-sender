#!/usr/bin/env python3
"""
HTTP streaming server for turntable audio.
Uses FFmpeg for capture + MP3 encoding, broadcasts to multiple HTTP clients.
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
            self.send_header('icy-name', 'Turntable')
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
                if client_queue in clients:
                    clients.remove(client_queue)
                logger.info(f"Client removed: {self.client_address[0]}")
                
        except Exception as e:
            logger.error(f"Stream error: {e}")


def ffmpeg_capture_thread(device="plughw:2,0", sample_rate=48000, bitrate="320k"):
    """
    Run FFmpeg to capture from ALSA and encode to MP3.
    Read MP3 data from stdout and broadcast to all clients.
    """
    global ffmpeg_process
    
    logger.info(f"🎤 Starting FFmpeg capture from {device}")
    
    # FFmpeg command: capture from ALSA, encode to MP3, output to stdout
    cmd = [
        'ffmpeg',
        '-f', 'alsa',
        '-i', device,
        '-acodec', 'libmp3lame',
        '-ab', bitrate,
        '-ac', '2',
        '-ar', str(sample_rate),
        '-f', 'mp3',
        '-'  # Output to stdout
    ]
    
    try:
        ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=8192
        )
        
        logger.info("✅ FFmpeg started, encoding to MP3")
        
        # Start a thread to monitor FFmpeg stderr for errors
        def log_ffmpeg_stderr():
            for line in ffmpeg_process.stderr:
                line_str = line.decode().strip()
                if line_str:
                    logger.warning(f"FFmpeg: {line_str}")
        
        stderr_thread = threading.Thread(target=log_ffmpeg_stderr, daemon=True)
        stderr_thread.start()
        
        # Read MP3 data and broadcast to all clients
        chunk_size = 8192
        bytes_read = 0
        while is_running:
            try:
                mp3_data = ffmpeg_process.stdout.read(chunk_size)
                
                if not mp3_data:
                    logger.warning("FFmpeg stopped producing data")
                    break
                
                bytes_read += len(mp3_data)
                if bytes_read % (8192 * 100) == 0:  # Log every ~800KB
                    logger.debug(f"Streamed {bytes_read // 1024}KB so far")
                
                # Broadcast to all connected clients
                if clients:
                    dead_clients = []
                    for client_queue in clients:
                        try:
                            client_queue.put_nowait(mp3_data)
                        except queue.Full:
                            # Client queue full, drop this chunk
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
                    logger.error(f"FFmpeg read error: {e}")
                break
                
    except FileNotFoundError:
        logger.error("FFmpeg not found! Install with: sudo apt-get install ffmpeg")
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
    finally:
        if ffmpeg_process:
            ffmpeg_process.terminate()
            try:
                ffmpeg_process.wait(timeout=5)
            except:
                ffmpeg_process.kill()
        logger.info("FFmpeg stopped")


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
    global is_running
    
    # Configuration
    PORT = 8000
    DEVICE = "plughw:2,0"
    SAMPLE_RATE = 48000
    BITRATE = "320k"
    
    local_ip = get_local_ip()
    
    print("\n" + "=" * 60)
    print("🎵 Turntable Streaming Server v2")
    print("=" * 60)
    print(f"\n📻 Audio Source: {DEVICE}")
    print(f"🌐 Stream URL:   http://{local_ip}:{PORT}/turntable.mp3")
    print(f"📊 Quality:      MP3 {BITRATE}, {SAMPLE_RATE}Hz, Stereo")
    print(f"\n✅ Supports multiple simultaneous listeners")
    print(f"✅ Properly encoded MP3 stream for Sonos")
    print(f"\n💡 To play on Sonos:")
    print(f"   python3 play_on_sonos.py")
    print(f"\n⏹️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start FFmpeg capture in background thread
    capture_thread = threading.Thread(
        target=ffmpeg_capture_thread,
        args=(DEVICE, SAMPLE_RATE, BITRATE),
        daemon=True
    )
    capture_thread.start()
    
    # Give FFmpeg a moment to start
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

