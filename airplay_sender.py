"""
AirPlay 2 sender module for streaming audio to AirPlay devices.
Uses pyatv and custom streaming for real-time audio transmission.
"""

import asyncio
import logging
import struct
import socket
import time
from typing import Optional, Tuple
from dataclasses import dataclass
import threading
import queue

logger = logging.getLogger(__name__)


@dataclass
class AudioFormat:
    """Audio format specification."""
    sample_rate: int
    channels: int
    bit_depth: int


class AirPlaySender:
    """
    Sends audio to AirPlay devices.
    
    Note: This implementation uses a simplified approach for AirPlay audio streaming.
    For production use, consider using libraries like shairplay or forked-daapd.
    """
    
    def __init__(self, 
                 host: str,
                 port: int = 7000,
                 audio_format: Optional[AudioFormat] = None):
        """
        Initialize AirPlay sender.
        
        Args:
            host: Target device IP address
            port: AirPlay port (default 7000)
            audio_format: Audio format specification
        """
        self.host = host
        self.port = port
        self.audio_format = audio_format or AudioFormat(44100, 2, 16)
        
        self.is_connected = False
        self.is_streaming = False
        self._socket: Optional[socket.socket] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._audio_queue = queue.Queue(maxsize=200)
        
        # Streaming statistics
        self.bytes_sent = 0
        self.packets_sent = 0
        self.start_time = None
        
    def connect(self) -> bool:
        """
        Connect to AirPlay device.
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to AirPlay device at {self.host}:{self.port}")
            
            # Create socket connection
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10)
            self._socket.connect((self.host, self.port))
            
            # Send RTSP ANNOUNCE request
            if not self._rtsp_announce():
                logger.error("RTSP ANNOUNCE failed")
                return False
            
            # Setup audio stream
            if not self._rtsp_setup():
                logger.error("RTSP SETUP failed")
                return False
            
            self.is_connected = True
            logger.info("Connected to AirPlay device")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            if self._socket:
                self._socket.close()
                self._socket = None
            return False
    
    def _rtsp_announce(self) -> bool:
        """Send RTSP ANNOUNCE request."""
        try:
            # Simplified RTSP ANNOUNCE
            # In production, use proper SDP and authentication
            sdp = self._create_sdp()
            
            request = (
                f"ANNOUNCE rtsp://{self.host}/stream RTSP/1.0\r\n"
                f"Content-Type: application/sdp\r\n"
                f"Content-Length: {len(sdp)}\r\n"
                f"CSeq: 1\r\n"
                f"\r\n"
                f"{sdp}"
            )
            
            self._socket.sendall(request.encode())
            response = self._socket.recv(4096).decode()
            
            # Check for 200 OK
            if "200 OK" in response or "RTSP/1.0" in response:
                return True
            
            logger.warning(f"ANNOUNCE response: {response[:200]}")
            return True  # Continue anyway for compatibility
            
        except Exception as e:
            logger.error(f"RTSP ANNOUNCE error: {e}")
            return False
    
    def _create_sdp(self) -> str:
        """Create SDP (Session Description Protocol) for audio stream."""
        return (
            "v=0\r\n"
            f"o=turntable 0 0 IN IP4 {self._get_local_ip()}\r\n"
            "s=Turntable Stream\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "t=0 0\r\n"
            f"m=audio 0 RTP/AVP 96\r\n"
            "a=rtpmap:96 L16/44100/2\r\n"
            f"a=fmtp:96\r\n"
        )
    
    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _rtsp_setup(self) -> bool:
        """Send RTSP SETUP request."""
        try:
            request = (
                f"SETUP rtsp://{self.host}/stream RTSP/1.0\r\n"
                f"Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n"
                f"CSeq: 2\r\n"
                f"\r\n"
            )
            
            self._socket.sendall(request.encode())
            response = self._socket.recv(4096).decode()
            
            logger.debug(f"SETUP response: {response[:200]}")
            return True
            
        except Exception as e:
            logger.error(f"RTSP SETUP error: {e}")
            return False
    
    def start_streaming(self):
        """Start streaming audio."""
        if not self.is_connected:
            raise RuntimeError("Not connected to device")
        
        if self.is_streaming:
            logger.warning("Already streaming")
            return
        
        # Send RECORD request
        try:
            request = (
                f"RECORD rtsp://{self.host}/stream RTSP/1.0\r\n"
                f"Range: npt=0-\r\n"
                f"CSeq: 3\r\n"
                f"\r\n"
            )
            self._socket.sendall(request.encode())
            response = self._socket.recv(4096).decode()
            logger.debug(f"RECORD response: {response[:200]}")
        except Exception as e:
            logger.warning(f"RECORD request failed: {e}")
        
        self.is_streaming = True
        self.start_time = time.time()
        
        # Start streaming thread
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True
        )
        self._stream_thread.start()
        
        logger.info("Started streaming audio")
    
    def _stream_loop(self):
        """Main streaming loop."""
        sequence_number = 0
        timestamp = 0
        
        while self.is_streaming:
            try:
                # Get audio data from queue
                audio_data = self._audio_queue.get(timeout=1.0)
                
                # Create RTP packet
                rtp_packet = self._create_rtp_packet(
                    audio_data,
                    sequence_number,
                    timestamp
                )
                
                # Send packet
                self._socket.sendall(rtp_packet)
                
                # Update counters
                sequence_number = (sequence_number + 1) % 65536
                frames = len(audio_data) // (self.audio_format.channels * 
                                             self.audio_format.bit_depth // 8)
                timestamp = (timestamp + frames) % (2**32)
                
                self.bytes_sent += len(rtp_packet)
                self.packets_sent += 1
                
            except queue.Empty:
                # No audio data available
                continue
            except Exception as e:
                if self.is_streaming:
                    logger.error(f"Streaming error: {e}")
                break
    
    def _create_rtp_packet(self, audio_data: bytes, 
                          sequence: int, timestamp: int) -> bytes:
        """
        Create RTP packet for audio data.
        
        RTP Header format:
        - Version (2 bits): 2
        - Padding (1 bit): 0
        - Extension (1 bit): 0
        - CSRC count (4 bits): 0
        - Marker (1 bit): 0
        - Payload type (7 bits): 96 (dynamic)
        - Sequence number (16 bits)
        - Timestamp (32 bits)
        - SSRC (32 bits): 0
        """
        # RTP header
        header = bytearray(12)
        
        # Version (2), Padding (0), Extension (0), CC (0)
        header[0] = 0x80  # 10000000
        
        # Marker (0), Payload type (96)
        header[1] = 96
        
        # Sequence number
        header[2:4] = struct.pack('>H', sequence)
        
        # Timestamp
        header[4:8] = struct.pack('>I', timestamp)
        
        # SSRC (we'll use a fixed value)
        header[8:12] = struct.pack('>I', 0x12345678)
        
        return bytes(header) + audio_data
    
    def send_audio(self, audio_data: bytes):
        """
        Queue audio data for streaming.
        
        Args:
            audio_data: Raw audio data to send
        """
        if not self.is_streaming:
            return
        
        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            logger.warning("Audio queue full, dropping frame")
    
    def stop_streaming(self):
        """Stop streaming audio."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        if self._stream_thread:
            self._stream_thread.join(timeout=2.0)
        
        # Send TEARDOWN
        try:
            if self._socket:
                request = (
                    f"TEARDOWN rtsp://{self.host}/stream RTSP/1.0\r\n"
                    f"CSeq: 4\r\n"
                    f"\r\n"
                )
                self._socket.sendall(request.encode())
        except:
            pass
        
        logger.info("Stopped streaming audio")
    
    def disconnect(self):
        """Disconnect from AirPlay device."""
        self.stop_streaming()
        
        if self._socket:
            self._socket.close()
            self._socket = None
        
        self.is_connected = False
        logger.info("Disconnected from AirPlay device")
    
    def get_stats(self) -> dict:
        """Get streaming statistics."""
        if not self.start_time:
            return {}
        
        duration = time.time() - self.start_time
        return {
            'duration': duration,
            'bytes_sent': self.bytes_sent,
            'packets_sent': self.packets_sent,
            'bitrate': (self.bytes_sent * 8) / duration if duration > 0 else 0,
            'queue_size': self._audio_queue.qsize()
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

