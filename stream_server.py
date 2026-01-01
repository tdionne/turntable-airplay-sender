#!/usr/bin/env python3
"""
HTTP streaming server for turntable audio.
Supports multiple simultaneous connections and auto-reconnect.
"""

import subprocess
import threading
import socket
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from audio_capture_alsa import AudioCaptureALSA
import queue
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global audio queue for broadcasting to all clients
audio_broadcast_queue = queue.Queue(maxsize=500)
is_running = True


class StreamHandler(BaseHTTPRequestHandler):
    """HTTP request handler for audio streaming."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"Client {self.client_address[0]}: {format % args}")
    
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
            self.end_headers()
            
            logger.info(f"✅ Client connected: {self.client_address[0]}")
            
            # Create client-specific queue
            client_queue = queue.Queue(maxsize=100)
            
            # Subscribe this client to broadcasts
            clients.append(client_queue)
            
            try:
                # Stream audio to client
                while is_running:
                    try:
                        # Get audio data (with timeout to allow checking is_running)
                        audio_data = client_queue.get(timeout=1.0)
                        
                        # Send to client
                        self.wfile.write(audio_data)
                        self.wfile.flush()
                        
                    except queue.Empty:
                        continue
                    except BrokenPipeError:
                        logger.info(f"Client disconnected: {self.client_address[0]}")
                        break
                    
            finally:
                # Unsubscribe client
                if client_queue in clients:
                    clients.remove(client_queue)
                logger.info(f"Client removed: {self.client_address[0]}")
                
        except Exception as e:
            logger.error(f"Stream error: {e}")


# List of connected clients
clients = []


def audio_capture_thread(device="plughw:2,0", sample_rate=48000):
    """Capture audio and broadcast to all clients."""
    logger.info(f"🎤 Starting audio capture from {device}")
    
    capture = AudioCaptureALSA(
        device=device,
        sample_rate=sample_rate,
        channels=2,
        chunk_size=4096,  # Larger chunks for streaming
        sample_width=16
    )
    
    def audio_callback(data):
        """Broadcast audio to all connected clients."""
        # Remove disconnected clients
        dead_clients = []
        for client_queue in clients:
            try:
                client_queue.put_nowait(data)
            except queue.Full:
                # Client not keeping up, skip this frame
                pass
            except Exception:
                dead_clients.append(client_queue)
        
        # Clean up dead clients
        for client in dead_clients:
            if client in clients:
                clients.remove(client)
    
    try:
        capture.start(callback=audio_callback)
        logger.info("✅ Audio capture started")
        
        # Keep thread alive
        import time
        while is_running:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Audio capture error: {e}")
    finally:
        capture.stop()
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
    global is_running
    logger.info("\n\nShutting down...")
    is_running = False
    sys.exit(0)


def main():
    """Main server function."""
    global is_running
    
    # Configuration
    PORT = 8000
    DEVICE = "plughw:2,0"
    SAMPLE_RATE = 48000
    
    local_ip = get_local_ip()
    
    print("\n" + "=" * 60)
    print("🎵 Turntable Streaming Server")
    print("=" * 60)
    print(f"\n📻 Audio Source: {DEVICE}")
    print(f"🌐 Stream URL:   http://{local_ip}:{PORT}/turntable.mp3")
    print(f"📊 Quality:      MP3 320kbps, {SAMPLE_RATE}Hz, Stereo")
    print(f"\n✅ Supports multiple simultaneous listeners")
    print(f"✅ Auto-reconnects on client disconnect")
    print(f"\n💡 To play on Sonos:")
    print(f"   python3 play_on_sonos.py")
    print(f"\n⏹️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start audio capture in background thread
    capture_thread = threading.Thread(
        target=audio_capture_thread,
        args=(DEVICE, SAMPLE_RATE),
        daemon=True
    )
    capture_thread.start()
    
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

