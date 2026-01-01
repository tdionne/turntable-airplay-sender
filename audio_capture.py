"""
Audio capture module for USB turntable input.
Handles real-time audio capture from USB audio devices.
"""

import pyaudio
import numpy as np
import logging
from typing import Optional, Callable
import threading
import queue

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captures audio from USB turntable or other audio input devices."""
    
    def __init__(self, 
                 device_index: Optional[int] = None,
                 device_name: Optional[str] = None,
                 sample_rate: int = 44100,
                 channels: int = 2,
                 chunk_size: int = 1024,
                 sample_width: int = 16):
        """
        Initialize audio capture.
        
        Args:
            device_index: Index of input device (None for default)
            device_name: ALSA device name (e.g., 'plughw:2,0') - alternative to index
            sample_rate: Sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Number of frames per buffer
            sample_width: Bits per sample (8, 16, 24, or 32)
        """
        self.device_index = device_index
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.sample_width = sample_width
        
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_running = False
        self.audio_queue = queue.Queue(maxsize=100)
        self._capture_thread: Optional[threading.Thread] = None
        
        # Audio processing settings
        self.volume_gain = 1.0
        self.normalize = False
        
    def list_devices(self):
        """List all available audio input devices."""
        devices = []
        
        # Get total device count across all host APIs
        num_devices = self.audio.get_device_count()
        
        for i in range(num_devices):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'sample_rate': int(device_info.get('defaultSampleRate'))
                    })
                    logger.info(f"Device {i}: {device_info.get('name')}")
            except Exception as e:
                logger.debug(f"Error querying device {i}: {e}")
                continue
        
        return devices
    
    def find_device_by_name(self, name_substring: str) -> Optional[int]:
        """
        Find device index by name substring (case-insensitive).
        
        Args:
            name_substring: Part of device name to search for
            
        Returns:
            Device index or None if not found
        """
        devices = self.list_devices()
        name_lower = name_substring.lower()
        
        for device in devices:
            if name_lower in device['name'].lower():
                logger.info(f"Found device: {device['name']} at index {device['index']}")
                return device['index']
        
        return None
    
    def get_audio_format(self):
        """Get PyAudio format based on sample width."""
        formats = {
            8: pyaudio.paInt8,
            16: pyaudio.paInt16,
            24: pyaudio.paInt24,
            32: pyaudio.paInt32
        }
        return formats.get(self.sample_width, pyaudio.paInt16)
    
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
            # If device_name provided, try to find it first
            device_to_use = self.device_index
            if self.device_name and not device_to_use:
                device_to_use = self.find_device_by_name(self.device_name)
                if device_to_use is None:
                    logger.warning(f"Device '{self.device_name}' not found, using default")
            
            self.stream = self.audio.open(
                format=self.get_audio_format(),
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_to_use,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback if not callback else None
            )
            
            self.is_running = True
            device_info = f"index {device_to_use}" if device_to_use is not None else "default"
            logger.info(f"Audio capture started: {self.sample_rate}Hz, "
                       f"{self.channels}ch, {self.sample_width}bit, device: {device_info}")
            
            if callback:
                self._capture_thread = threading.Thread(
                    target=self._capture_loop,
                    args=(callback,),
                    daemon=True
                )
                self._capture_thread.start()
                
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for PyAudio stream (non-blocking mode)."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            self.audio_queue.put_nowait(in_data)
        except queue.Full:
            logger.warning("Audio queue full, dropping frame")
        
        return (None, pyaudio.paContinue)
    
    def _capture_loop(self, callback: Callable):
        """Capture loop for blocking mode with callback."""
        while self.is_running:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Apply audio processing
                if self.normalize or self.volume_gain != 1.0:
                    data = self._process_audio(data)
                
                callback(data)
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error in capture loop: {e}")
                break
    
    def _process_audio(self, data: bytes) -> bytes:
        """Apply audio processing (normalization, gain, etc.)."""
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
        audio_float = np.clip(audio_float, -32768, 32767)
        
        # Convert back to int
        if self.sample_width == 16:
            processed = audio_float.astype(np.int16)
        else:
            processed = audio_float.astype(np.int32)
        
        return processed.tobytes()
    
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
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        logger.info("Audio capture stopped")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        self.audio.terminate()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()
        if hasattr(self, 'audio'):
            self.audio.terminate()

