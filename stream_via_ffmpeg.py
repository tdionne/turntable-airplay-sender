#!/usr/bin/env python3
"""
Alternative streaming using FFmpeg/avconv with pipe.
This is a more reliable approach than custom RTP implementation.
"""

import subprocess
import logging
import signal
from typing import Optional
from audio_capture_alsa import AudioCaptureALSA

logger = logging.getLogger(__name__)


class FFmpegAirPlayStreamer:
    """Stream audio via FFmpeg to HTTP/RTP endpoint."""
    
    def __init__(self, 
                 target_host: str,
                 target_port: int = 5000,
                 sample_rate: int = 48000,
                 channels: int = 2):
        self.target_host = target_host
        self.target_port = target_port
        self.sample_rate = sample_rate
        self.channels = channels
        self.process: Optional[subprocess.Popen] = None
        
    def start_ffmpeg_stream(self):
        """Start FFmpeg process for streaming."""
        # FFmpeg command to stream raw PCM to RTP
        cmd = [
            'ffmpeg',
            '-f', 's16le',  # Input format: signed 16-bit little-endian
            '-ar', str(self.sample_rate),  # Sample rate
            '-ac', str(self.channels),  # Channels
            '-i', 'pipe:0',  # Input from stdin
            '-acodec', 'pcm_s16le',  # Audio codec
            '-f', 'rtp',  # Output format
            f'rtp://{self.target_host}:{self.target_port}'
        ]
        
        logger.info(f"Starting FFmpeg stream to {self.target_host}:{self.target_port}")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info("FFmpeg process started")
            return True
        except FileNotFoundError:
            logger.error("FFmpeg not found. Install with: sudo apt-get install ffmpeg")
            return False
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            return False
    
    def write_audio(self, data: bytes):
        """Write audio data to FFmpeg stdin."""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
            except BrokenPipeError:
                logger.error("FFmpeg pipe broken")
            except Exception as e:
                logger.error(f"Error writing to FFmpeg: {e}")
    
    def stop(self):
        """Stop FFmpeg process."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
            logger.info("FFmpeg process stopped")


def stream_turntable_simple(alsa_device: str = "plughw:2,0",
                           target_host: str = "10.0.0.64",
                           sample_rate: int = 48000):
    """
    Simple streaming without AirPlay complexity.
    Captures from turntable and pipes to FFmpeg.
    """
    logger.info("🎵 Starting simple turntable streaming...")
    logger.info(f"   Source: {alsa_device}")
    logger.info(f"   Target: {target_host}")
    
    # Setup audio capture
    capture = AudioCaptureALSA(
        device=alsa_device,
        sample_rate=sample_rate,
        channels=2,
        chunk_size=1024,
        sample_width=16
    )
    
    # Setup FFmpeg streamer
    streamer = FFmpegAirPlayStreamer(
        target_host=target_host,
        target_port=5000,
        sample_rate=sample_rate,
        channels=2
    )
    
    def audio_callback(data):
        """Send captured audio to FFmpeg."""
        streamer.write_audio(data)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        logger.info("\nStopping...")
        capture.stop()
        streamer.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start streaming
        if not streamer.start_ffmpeg_stream():
            logger.error("Failed to start FFmpeg")
            return
        
        # Start capture
        capture.start(callback=audio_callback)
        
        logger.info("✅ Streaming started! Press Ctrl+C to stop.")
        
        # Keep running
        import time
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Streaming error: {e}")
    finally:
        capture.stop()
        streamer.stop()


if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "10.0.0.64"
    
    stream_turntable_simple(target_host=target)

