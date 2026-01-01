#!/usr/bin/env python3
"""
Turntable AirPlay Sender - Main entry point
Streams audio from USB turntable to Sonos via AirPlay 2
"""

import sys
import time
import signal
import logging
from pathlib import Path
from typing import Optional

import click
import yaml
import colorlog

from audio_capture import AudioCapture
from airplay_sender import AirPlaySender, AudioFormat
from device_discovery import discover_airplay_devices, find_device_by_name


# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    global running
    print("\n\nShutting down...")
    running = False


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup colored logging."""
    # Create colored formatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {}


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--config', '-c', default='config.yaml', 
              help='Path to configuration file')
@click.option('--device', '-d', help='Target AirPlay device name')
@click.option('--list-devices', is_flag=True, 
              help='List available audio input devices')
@click.option('--discover', is_flag=True, 
              help='Discover AirPlay devices on network')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(ctx, config, device, list_devices, discover, verbose):
    """Turntable AirPlay Sender - Stream turntable audio to Sonos via AirPlay 2."""
    
    # Load configuration
    cfg = load_config(config) if Path(config).exists() else {}
    
    # Setup logging
    log_level = "DEBUG" if verbose else cfg.get('logging', {}).get('level', 'INFO')
    log_file = cfg.get('logging', {}).get('log_file') if cfg.get('logging', {}).get('log_to_file') else None
    setup_logging(log_level, log_file)
    
    logger = logging.getLogger(__name__)
    
    # Handle special commands
    if list_devices:
        list_audio_devices()
        return
    
    if discover:
        discover_devices(cfg)
        return
    
    # If no subcommand, run the streamer
    if ctx.invoked_subcommand is None:
        if not device and not cfg.get('airplay_output', {}).get('device_name'):
            logger.error("No target device specified. Use --device or set in config.yaml")
            logger.info("Run with --discover to find available devices")
            sys.exit(1)
        
        device_name = device or cfg.get('airplay_output', {}).get('device_name')
        run_streamer(cfg, device_name)


def list_audio_devices():
    """List all available audio input devices."""
    print("\n📻 Available Audio Input Devices:\n")
    
    with AudioCapture() as capture:
        devices = capture.list_devices()
        
        if not devices:
            print("No audio input devices found.")
            return
        
        for dev in devices:
            print(f"  [{dev['index']}] {dev['name']}")
            print(f"      Channels: {dev['channels']}, Sample Rate: {dev['sample_rate']} Hz")
            print()


def discover_devices(cfg: dict):
    """Discover AirPlay devices on the network."""
    print("\n🔍 Discovering AirPlay devices...\n")
    
    timeout = cfg.get('network', {}).get('discovery_timeout', 10)
    devices = discover_airplay_devices(timeout)
    
    if not devices:
        print("No AirPlay devices found.")
        print("\nTroubleshooting:")
        print("  - Ensure devices are on the same network")
        print("  - Check that AirPlay is enabled on target devices")
        print("  - Verify firewall settings")
        return
    
    print(f"Found {len(devices)} AirPlay device(s):\n")
    for device in devices:
        print(f"  📱 {device.name}")
        print(f"     Address: {device.host}:{device.port}")
        print(f"     Model: {device.model}")
        print()


def run_streamer(cfg: dict, device_name: str):
    """Run the audio streamer."""
    logger = logging.getLogger(__name__)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🎵 Turntable AirPlay Sender Starting...")
    
    # Discover target device
    logger.info(f"Looking for device: {device_name}")
    timeout = cfg.get('network', {}).get('discovery_timeout', 10)
    target_device = find_device_by_name(device_name, timeout)
    
    if not target_device:
        logger.error(f"Device '{device_name}' not found")
        logger.info("Run with --discover to see available devices")
        sys.exit(1)
    
    logger.info(f"Found device: {target_device.name} at {target_device.host}")
    
    # Setup audio capture
    audio_cfg = cfg.get('audio_input', {})
    capture = AudioCapture(
        device_index=audio_cfg.get('device_index'),
        sample_rate=audio_cfg.get('sample_rate', 44100),
        channels=audio_cfg.get('channels', 2),
        chunk_size=audio_cfg.get('chunk_size', 1024),
        sample_width=audio_cfg.get('sample_width', 16)
    )
    
    # Apply audio processing settings
    processing_cfg = cfg.get('audio_processing', {})
    capture.normalize = processing_cfg.get('normalize', False)
    capture.volume_gain = processing_cfg.get('volume_gain', 1.0)
    
    # Setup AirPlay sender
    audio_format = AudioFormat(
        sample_rate=capture.sample_rate,
        channels=capture.channels,
        bit_depth=capture.sample_width
    )
    
    sender = AirPlaySender(
        host=target_device.host,
        port=target_device.port,
        audio_format=audio_format
    )
    
    try:
        # Connect to AirPlay device
        logger.info("Connecting to AirPlay device...")
        if not sender.connect():
            logger.error("Failed to connect to AirPlay device")
            sys.exit(1)
        
        # Start streaming
        sender.start_streaming()
        
        # Start audio capture with callback
        def audio_callback(data):
            sender.send_audio(data)
        
        capture.start(callback=audio_callback)
        
        logger.info("✅ Streaming started! Press CTRL+C to stop.")
        logger.info(f"   Input: USB Turntable ({capture.sample_rate}Hz, {capture.channels}ch)")
        logger.info(f"   Output: {target_device.name} via AirPlay 2")
        
        # Main loop - print stats periodically
        last_stats_time = time.time()
        
        while running:
            time.sleep(1)
            
            # Print stats every 30 seconds
            if time.time() - last_stats_time > 30:
                stats = sender.get_stats()
                if stats:
                    duration = stats['duration']
                    bitrate_kbps = stats['bitrate'] / 1000
                    logger.info(f"📊 Stats: {int(duration)}s streamed, "
                              f"{stats['packets_sent']} packets, "
                              f"{bitrate_kbps:.1f} kbps")
                last_stats_time = time.time()
        
    except Exception as e:
        logger.error(f"Error during streaming: {e}", exc_info=True)
        
    finally:
        # Cleanup
        logger.info("Stopping streaming...")
        capture.stop()
        sender.disconnect()
        logger.info("✅ Shutdown complete")


@cli.command()
@click.option('--config', '-c', default='config.yaml')
def test(config):
    """Test audio capture without streaming."""
    cfg = load_config(config) if Path(config).exists() else {}
    setup_logging("INFO")
    
    logger = logging.getLogger(__name__)
    logger.info("🎤 Testing audio capture...")
    
    audio_cfg = cfg.get('audio_input', {})
    
    with AudioCapture(
        device_index=audio_cfg.get('device_index'),
        sample_rate=audio_cfg.get('sample_rate', 44100),
        channels=audio_cfg.get('channels', 2),
        chunk_size=audio_cfg.get('chunk_size', 1024)
    ) as capture:
        
        def callback(data):
            # Just count frames
            pass
        
        capture.start(callback=callback)
        logger.info("✅ Capturing audio for 5 seconds...")
        time.sleep(5)
        
    logger.info("✅ Test complete")


if __name__ == '__main__':
    cli()

