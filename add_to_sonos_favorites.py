#!/usr/bin/env python3
"""
Add turntable stream to Sonos favorites.
After running this once, family can play "Turntable" from Sonos app.
"""

import soco
import socket
import sys

def get_local_ip():
    """Get local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def add_to_favorites():
    """Add turntable stream to Sonos favorites."""
    print("=" * 60)
    print("🎵 Add Turntable to Sonos Favorites")
    print("=" * 60)
    print()
    
    # Get stream URL
    local_ip = get_local_ip()
    stream_url = f"http://{local_ip}:8000/turntable.mp3"
    
    print(f"Stream URL: {stream_url}")
    print()
    
    # Discover any Sonos speaker
    print("🔍 Finding Sonos speaker...")
    speakers = list(soco.discover())
    
    if not speakers:
        print("❌ No Sonos speakers found")
        return
    
    speaker = speakers[0]
    print(f"✅ Using: {speaker.player_name}")
    print()
    
    try:
        # Try to add the stream directly to Sonos
        # Note: This creates a temporary entry, not a permanent favorite
        print("Adding stream to Sonos...")
        
        # Create a music library entry (requires coordinator)
        # For now, we'll provide manual instructions
        
        print("⚠️  Sonos doesn't support programmatically adding HTTP streams to favorites.")
        print()
        print("📝 MANUAL SETUP (One-Time):")
        print()
        print("1. Ensure stream is running: python3 stream_server_v2.py")
        print()
        print("2. Open Sonos app on your phone/tablet")
        print()
        print("3. Go to: Browse → TuneIn")
        print("   (If you don't have TuneIn, it's FREE - you don't need the paid version)")
        print()
        print("4. Scroll down to 'My Radio Stations'")
        print()
        print("5. Tap the three dots (⋯) or settings icon")
        print()
        print("6. Select 'Add New Radio Station'")
        print()
        print("7. Enter:")
        print(f"   Name: Turntable")
        print(f"   URL:  {stream_url}")
        print()
        print("8. Save!")
        print()
        print("✅ After this one-time setup:")
        print("   - 'Turntable' will appear in TuneIn → My Radio Stations")
        print("   - Anyone can select it from the Sonos app")
        print("   - No subscription needed (TuneIn basic is free)")
        print()
        print("💡 Alternative: Add to Sonos Favorites")
        print("   - Play the Turntable station once")
        print("   - Tap the heart icon to add to Favorites")
        print("   - Now it's in your main Favorites list!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_to_favorites()

