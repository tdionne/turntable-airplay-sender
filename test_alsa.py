#!/usr/bin/env python3
"""
Simple test script for ALSA audio capture.
Tests capturing audio directly from USB turntable using ALSA.
"""

import alsaaudio
import sys
import time
import subprocess
import re

def test_alsa_device(device_string):
    """Test capturing from ALSA device."""
    print(f"\n🔍 Testing ALSA device: {device_string}")
    print("=" * 60)
    
    try:
        # Open PCM device for capture
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            device=device_string
        )
        
        # Set parameters
        pcm.setchannels(2)
        pcm.setrate(48000)
        pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        pcm.setperiodsize(1024)
        
        print("✅ Device opened successfully!")
        print("   Sample rate: 48000 Hz")
        print("   Channels: 2 (stereo)")
        print("   Format: 16-bit PCM")
        print()
        print("🎙️  Recording 3 seconds of test audio...")
        
        # Capture for 3 seconds
        frames_captured = 0
        start_time = time.time()
        
        while time.time() - start_time < 3.0:
            length, data = pcm.read()
            if length > 0:
                frames_captured += length
                if frames_captured % 10240 == 0:
                    print(".", end="", flush=True)
        
        print()
        print(f"\n✅ SUCCESS! Captured {frames_captured} frames")
        print()
        print("💡 Use this device string in config.yaml:")
        print(f"   audio_input:")
        print(f"     use_alsa: true")
        print(f"     alsa_device: '{device_string}'")
        
        pcm.close()
        return True
        
    except alsaaudio.ALSAAudioError as e:
        print(f"❌ ALSA Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_arecord_devices():
    """Parse arecord -l to get actual card numbers."""
    try:
        result = subprocess.run(['arecord', '-l'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        
        devices = []
        for line in result.stdout.split('\n'):
            # Look for lines like: card 2: CODEC [USB AUDIO  CODEC], device 0: USB Audio [USB Audio]
            match = re.match(r'card (\d+): (\w+) \[([^\]]+)\]', line)
            if match:
                card_num = int(match.group(1))
                card_id = match.group(2)
                card_name = match.group(3)
                devices.append({
                    'card': card_num,
                    'id': card_id,
                    'name': card_name,
                    'device_string': f"plughw:{card_num},0"
                })
        
        return devices
    except Exception as e:
        print(f"Error running arecord: {e}")
        return []


def list_alsa_cards():
    """List all ALSA sound cards."""
    print("\n📻 ALSA Sound Cards (from arecord -l):")
    print("=" * 60)
    
    devices = get_arecord_devices()
    
    if not devices:
        print("No capture devices found")
        print("\nTry running: arecord -l")
        return []
    
    device_strings = []
    
    for dev in devices:
        print(f"\n  Card {dev['card']}: {dev['name']}")
        print(f"    Device: {dev['device_string']}")
        device_strings.append(dev['device_string'])
    
    return device_strings


if __name__ == "__main__":
    print("=" * 60)
    print("ALSA Audio Capture Test")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Test specific device
        device = sys.argv[1]
        test_alsa_device(device)
    else:
        # List cards and test each
        device_strings = list_alsa_cards()
        
        if device_strings:
            print("\n" + "=" * 60)
            print("Testing each device for audio capture...")
            print("=" * 60)
            
            for device in device_strings:
                if test_alsa_device(device):
                    print("\n✅ Found working device!")
                    break
                print()
        else:
            print("\n❌ No ALSA devices found")
            print("\nCheck with: arecord -l")

