#!/usr/bin/env python3
"""
Test script for auto-play detection.
Monitors audio levels from the turntable without starting the full server.
"""

import alsaaudio
import numpy as np
import time
import sys

def calculate_rms(audio_data):
    """Calculate RMS level from raw audio data."""
    samples = np.frombuffer(audio_data, dtype=np.int16)
    if len(samples) == 0:
        return 0
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return int(rms)


def main():
    DEVICE = "plughw:2,0"
    SAMPLE_RATE = 48000
    THRESHOLD = 500
    TRIGGER_DELAY = 2.0
    
    print("\n" + "=" * 60)
    print("🎵 Auto-Play Detection Test")
    print("=" * 60)
    print(f"\n📻 Device:        {DEVICE}")
    print(f"🎚️  Threshold:     {THRESHOLD}")
    print(f"⏱️  Trigger delay: {TRIGGER_DELAY}s")
    print(f"\n💡 Drop the needle on your turntable to test detection")
    print(f"⏹️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    try:
        # Open ALSA device
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            device=DEVICE,
            channels=2,
            rate=SAMPLE_RATE,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=1024
        )
        print(f"✅ ALSA device opened successfully\n")
        
        trigger_time = None
        triggered = False
        
        while True:
            # Read audio
            length, pcm_data = pcm.read()
            
            if length <= 0:
                time.sleep(0.001)
                continue
            
            # Calculate RMS level
            rms_level = calculate_rms(pcm_data)
            
            # Display level with visual bar
            bar_length = int(rms_level / 100)
            bar = "█" * min(bar_length, 60)
            
            if rms_level > THRESHOLD:
                # Above threshold
                if trigger_time is None:
                    trigger_time = time.time()
                    print(f"\n🎵 Audio detected! RMS={rms_level}")
                    print(f"   Waiting {TRIGGER_DELAY}s to confirm...")
                else:
                    elapsed = time.time() - trigger_time
                    if elapsed >= TRIGGER_DELAY and not triggered:
                        print(f"\n✅ TRIGGER! Would start Sonos playback now!")
                        print(f"   (RMS level: {rms_level})")
                        triggered = True
                    else:
                        print(f"   {elapsed:.1f}s / {TRIGGER_DELAY}s - RMS={rms_level} {bar}")
            else:
                # Below threshold
                if trigger_time is not None and not triggered:
                    print(f"   Audio dropped below threshold, resetting")
                    trigger_time = None
                
                # Show quiet levels occasionally
                if int(time.time() * 10) % 10 == 0:
                    print(f"🔇 Quiet: RMS={rms_level:4d} (threshold={THRESHOLD}) {bar}", end='\r')
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

