#!/usr/bin/env python3
"""
Test script to directly open USB audio device bypassing PyAudio enumeration.
"""

import pyaudio
import sys

def test_device(device_index):
    """Test opening a specific device for audio capture."""
    p = pyaudio.PyAudio()
    
    print(f"\n🔍 Testing device index {device_index}...")
    
    try:
        # Get device info
        try:
            info = p.get_device_info_by_index(device_index)
            print(f"Device name: {info['name']}")
            print(f"Max input channels (reported): {info['maxInputChannels']}")
            print(f"Default sample rate: {info['defaultSampleRate']}")
        except Exception as e:
            print(f"Could not get device info: {e}")
        
        # Try to open the device anyway
        print("\nAttempting to open device for recording...")
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=48000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        print("✅ SUCCESS! Device opened successfully!")
        print("Recording 2 seconds of test audio...")
        
        # Record some test audio
        frames = []
        for i in range(0, int(48000 / 1024 * 2)):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            if i % 20 == 0:
                print(".", end="", flush=True)
        
        print("\n✅ Recording successful!")
        
        stream.stop_stream()
        stream.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
        
    finally:
        p.terminate()


if __name__ == "__main__":
    print("=" * 60)
    print("USB Audio Device Test")
    print("=" * 60)
    
    # Based on arecord -l showing card 2
    # PyAudio device indices don't always match ALSA card numbers
    # We'll try common indices
    
    if len(sys.argv) > 1:
        # Test specific device
        device_idx = int(sys.argv[1])
        test_device(device_idx)
    else:
        # Try all devices
        print("\nTrying all device indices...\n")
        
        for idx in range(10):
            if test_device(idx):
                print(f"\n🎉 Device {idx} works! Use this in your config.yaml")
                print(f"\naudio_input:")
                print(f"  device_index: {idx}")
                break
        else:
            print("\n❌ No working devices found")
            print("\nTroubleshooting:")
            print("1. Check device with: arecord -l")
            print("2. Test ALSA directly: arecord -D plughw:2,0 -f cd -d 2 test.wav")
            print("3. Try: python3 test_usb_audio.py <device_number>")

