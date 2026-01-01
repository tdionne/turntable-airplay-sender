"""
ALSA-based audio capture module for USB turntable input.
This is an alternative to PyAudio that works better on Raspberry Pi.
"""

import alsaaudio
import numpy as np
import logging
from typing import Optional, Callable
import threading
import queue
import time
import subprocess
import re

logger = logging.getLogger(__name__)


class AudioCaptureALSA:
    """Captures audio from USB turntable using ALSA directly."""
    
    def __init__(self, 
                 device: str = "plughw:2,0",
                 sample_rate: int = 48000,
                 channels: int = 2,
                 chunk_size: int = 1024,
                 sample_width: int = 16):
        """
        Initialize ALSA audio capture.
        
        Args:
            device: ALSA device string (e.g., "plughw:2,0" for card 2)
            sample_rate: Sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Number of frames per buffer
            sample_width: Bits per sample (16 or 32)
        """
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.sample_width = sample_width
        
        self.pcm: Optional[alsaaudio.PCM] = None
        self.is_running = False
        self.audio_queue = queue.Queue(maxsize=100)
        self._capture_thread: Optional[threading.Thread] = None
        
        # Audio processing settings
        self.volume_gain = 1.0
        self.normalize = False
        
    @staticmethod
    def list_devices():
        """List all available ALSA capture devices."""
        devices = []
        
        try:
            # Use arecord -l to get actual card numbers
            result = subprocess.run(['arecord', '-l'], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            for line in result.stdout.split('\n'):
                # Look for lines like: card 2: CODEC [USB AUDIO  CODEC], device 0: USB Audio [USB Audio]
                match = re.match(r'card (\d+): (\w+) \[([^\]]+)\]', line)
                if match:
                    card_num = int(match.group(1))
                    card_id = match.group(2)
                    card_name = match.group(3)
                    device_string = f"plughw:{card_num},0"
                    
                    devices.append({
                        'card': card_num,
                        'id': card_id,
                        'name': card_name,
                        'device_string': device_string
                    })
                    logger.info(f"Card {card_num}: {card_name} ({device_string})")
                        
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running arecord: {e}")
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
        
        return devices
    
    def get_alsa_format(self):
        """Get ALSA format based on sample width."""
        if self.sample_width == 8:
            return alsaaudio.PCM_FORMAT_S8
        elif self.sample_width == 16:
            return alsaaudio.PCM_FORMAT_S16_LE
        elif self.sample_width == 24:
            return alsaaudio.PCM_FORMAT_S24_LE
        elif self.sample_width == 32:
            return alsaaudio.PCM_FORMAT_S32_LE
        else:
            logger.warning(f"Unsupported sample width {self.sample_width}, using 16")
            return alsaaudio.PCM_FORMAT_S16_LE
    
    def start(self, callback: Optional[Callable] = None):
        """
        Start capturing audio.
        
        Args:
            callback: Optional callback function for audio data
        """
        if self.is_running:
            logger.warning("Audio capture already running")
            return
        
        try:
            # Open ALSA PCM device
            logger.info(f"Opening ALSA device: {self.device}")
            
            self.pcm = alsaaudio.PCM(
                type=alsaaudio.PCM_CAPTURE,
                mode=alsaaudio.PCM_NORMAL,
                device=self.device
            )
            
            # Set parameters
            self.pcm.setchannels(self.channels)
            self.pcm.setrate(self.sample_rate)
            self.pcm.setformat(self.get_alsa_format())
            self.pcm.setperiodsize(self.chunk_size)
            
            self.is_running = True
            logger.info(f"ALSA audio capture started: {self.sample_rate}Hz, "
                       f"{self.channels}ch, {self.sample_width}bit, device: {self.device}")
            
            # Start capture thread
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                args=(callback,),
                daemon=True
            )
            self._capture_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start ALSA audio capture: {e}")
            raise
    
    def _capture_loop(self, callback: Optional[Callable]):
        """Capture loop for reading from ALSA."""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running:
            try:
                # Read audio data from ALSA
                length, data = self.pcm.read()
                
                if length > 0:
                    consecutive_errors = 0  # Reset error counter
                    
                    # Apply audio processing if needed
                    if self.normalize or self.volume_gain != 1.0:
                        data = self._process_audio(data)
                    
                    # Call callback or queue data
                    if callback:
                        callback(data)
                    else:
                        try:
                            self.audio_queue.put_nowait(data)
                        except queue.Full:
                            logger.warning("Audio queue full, dropping frame")
                else:
                    # No data available, short sleep
                    time.sleep(0.001)
                    
            except alsaaudio.ALSAAudioError as e:
                consecutive_errors += 1
                logger.warning(f"ALSA read error: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping")
                    self.is_running = False
                    break
                    
                time.sleep(0.1)  # Brief pause before retry
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error in capture loop: {e}")
                break
    
    def _process_audio(self, data: bytes) -> bytes:
        """Apply audio processing (normalization, gain, etc.)."""
        try:
            # Convert to numpy array
            if self.sample_width == 16:
                audio_data = np.frombuffer(data, dtype=np.int16)
            elif self.sample_width == 32:
                audio_data = np.frombuffer(data, dtype=np.int32)
            else:
                return data  # Unsupported format, return as-is
            
            # Convert to float for processing
            audio_float = audio_data.astype(np.float32)
            
            # Normalize
            if self.normalize:
                max_val = np.abs(audio_float).max()
                if max_val > 0:
                    audio_float = audio_float / max_val * 32767
            
            # Apply gain
            audio_float = audio_float * self.volume_gain
            
            # Clip to prevent overflow
            if self.sample_width == 16:
                audio_float = np.clip(audio_float, -32768, 32767)
            else:
                audio_float = np.clip(audio_float, -2147483648, 2147483647)
            
            # Convert back to int
            if self.sample_width == 16:
                processed = audio_float.astype(np.int16)
            else:
                processed = audio_float.astype(np.int32)
            
            return processed.tobytes()
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return data  # Return original on error
    
    def read(self) -> Optional[bytes]:
        """
        Read audio data from queue (non-blocking).
        
        Returns:
            Audio data bytes or None if queue is empty
        """
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        """Stop capturing audio."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for thread to finish
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        
        if self.pcm:
            try:
                self.pcm.close()
            except:
                pass
            self.pcm = None
        
        logger.info("ALSA audio capture stopped")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()

