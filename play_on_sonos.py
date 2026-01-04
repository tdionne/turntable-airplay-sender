#!/usr/bin/env python3
"""
Direct Sonos control - play turntable stream without TuneIn
Uses SoCo library to directly command Sonos to play the HTTP stream
"""

import soco
import sys
import time
import socket

def get_local_ip():
    """Get local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def discover_sonos():
    """Discover all Sonos speakers on network."""
    print("🔍 Discovering Sonos speakers...")
    discovered = soco.discover()
    speakers = list(discovered) if discovered else []
    
    if not speakers:
        print("❌ No Sonos speakers found")
        print("   Make sure they're on the same network")
        return []
    
    print(f"\n✅ Found {len(speakers)} Sonos speaker(s):\n")
    for idx, speaker in enumerate(speakers):
        print(f"  [{idx}] {speaker.player_name}")
        print(f"      IP: {speaker.ip_address}")
        print(f"      Model: {speaker.get_speaker_info().get('model_name', 'Unknown')}")
        print()
    
    return speakers

def play_stream_on_sonos(speaker, stream_url):
    """
    Play HTTP stream on Sonos speaker.
    
    Args:
        speaker: SoCo speaker object
        stream_url: HTTP stream URL
    """
    print(f"▶️  Playing on: {speaker.player_name}")
    print(f"   Stream: {stream_url}")
    
    try:
        # Stop current playback
        speaker.stop()
        time.sleep(0.5)
        
        # Clear queue
        speaker.clear_queue()
        time.sleep(0.5)
        
        # Play the stream URL
        # For HTTP streams, we can use the direct URI
        speaker.play_uri(stream_url, title="Turntable")
        
        print("✅ Stream started!")
        print(f"   Volume: {speaker.volume}%")
        print(f"   Status: {speaker.get_current_transport_info()['current_transport_state']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function."""
    print("=" * 60)
    print("🎵 Turntable → Sonos Direct Player")
    print("=" * 60)
    print()
    
    # Get stream URL
    local_ip = get_local_ip()
    stream_url = f"http://{local_ip}:8000/turntable.mp3"
    
    # Discover speakers
    speakers = discover_sonos()
    
    if not speakers:
        sys.exit(1)
    
    # Select speaker
    if len(sys.argv) > 1:
        # Speaker name provided as argument
        target_name = sys.argv[1]
        speaker = None
        for s in speakers:
            if target_name.lower() in s.player_name.lower():
                speaker = s
                break
        
        if not speaker:
            print(f"❌ Speaker '{target_name}' not found")
            sys.exit(1)
    
    elif len(speakers) == 1:
        # Only one speaker, use it
        speaker = speakers[0]
    
    else:
        # Multiple speakers, ask user
        print("Select a speaker:")
        try:
            choice = int(input("Enter number: "))
            if 0 <= choice < len(speakers):
                speaker = speakers[choice]
            else:
                print("Invalid choice")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled")
            sys.exit(1)
    
    print()
    
    # Check if stream is available
    import urllib.request
    try:
        urllib.request.urlopen(stream_url, timeout=2)
    except:
        print("⚠️  Warning: Stream server doesn't appear to be running")
        print(f"   Make sure to run: ./turntable-stream.sh")
        print()
        response = input("Try to play anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Play!
    play_stream_on_sonos(speaker, stream_url)
    
    print()
    print("💡 Tip: To stop, use the Sonos app or run:")
    print(f"   python3 {sys.argv[0]} --stop")

if __name__ == "__main__":
    main()

