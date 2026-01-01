#!/usr/bin/env python3
"""
Create playlist files for the turntable stream.
These can be added to Sonos music library.
"""

import socket
import os

def get_local_ip():
    """Get local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def create_playlists():
    """Create M3U playlist file."""
    local_ip = get_local_ip()
    stream_url = f"http://{local_ip}:8000/turntable.mp3"
    
    # Create M3U playlist (most compatible with Sonos)
    m3u_content = f"""#EXTM3U
#EXTINF:-1,Turntable
{stream_url}
"""
    
    with open('/root/turntable-airplay-sender/turntable.m3u', 'w') as f:
        f.write(m3u_content)
    
    print("=" * 60)
    print("🎵 Playlist File Created")
    print("=" * 60)
    print()
    print(f"✅ Created: /root/turntable-airplay-sender/turntable.m3u")
    print()
    print(f"📻 Stream URL: {stream_url}")
    print()
    print("=" * 60)
    print("HOW TO ADD TO SONOS (Choose One):")
    print("=" * 60)
    print()
    print("METHOD 1: Via File Share (Most Family-Friendly)")
    print("-" * 60)
    print("1. Install Samba on your Pi:")
    print("   sudo apt-get install samba")
    print()
    print("2. Share this folder via Samba")
    print()
    print("3. In Sonos app:")
    print("   Settings → Manage → Music Library Settings → Add")
    print(f"   Path: //10.0.0.30/turntable-airplay-sender")
    print()
    print("4. Playlist will appear in: Browse → Music Library → Imported Playlists")
    print()
    print()
    print("METHOD 2: Via TuneIn (Easiest)")
    print("-" * 60)
    print("1. Open Sonos app")
    print("2. Browse → TuneIn → My Radio Stations")
    print("3. Add New Radio Station:")
    print("   Name: Turntable")
    print(f"   URL:  {stream_url}")
    print()
    print("✅ TuneIn basic is FREE (no subscription needed)")
    print()
    print()
    print("METHOD 3: Via Sonos Favorites")
    print("-" * 60)
    print("1. Use: python3 play_on_sonos.py 'Living Room'")
    print("2. While playing, open Sonos app")
    print("3. Tap the ♡ (heart) icon to add to Favorites")
    print("4. Now anyone can play from Favorites!")
    print()

if __name__ == "__main__":
    create_playlists()

