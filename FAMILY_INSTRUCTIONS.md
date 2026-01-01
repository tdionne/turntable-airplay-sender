# How to Play the Turntable on Sonos

Simple instructions for family members to play vinyl throughout the house!

## Quick Start (After Initial Setup)

### Using the Sonos App

1. **Make sure the turntable stream is running** (it should auto-start when the Raspberry Pi is on)

2. **Open the Sonos app** on your phone or tablet

3. **Find "Turntable" in one of these places:**
   - **Browse → TuneIn → My Radio Stations → Turntable**
   - **Browse → Favorites → Turntable** (if added to favorites)

4. **Tap to play!** 🎵

5. **Put a record on the turntable**

That's it! The turntable audio will play on your selected Sonos speaker(s).

---

## Tips

### Play on Multiple Speakers

1. In Sonos app, create a **Group** with multiple rooms
2. Play "Turntable" on the group
3. Now vinyl plays everywhere!

### Add to Favorites (One-Time)

1. Play "Turntable" from TuneIn
2. Tap the **♡ (heart)** icon while it's playing
3. Now it's in your main Favorites list for quick access!

### Adjust Volume

Use the Sonos app volume controls as normal. The turntable stream will play at whatever volume you set.

---

## Troubleshooting

### "Unable to play - stream not available"

**The stream server isn't running.** Ask the person who set this up to:
```bash
ssh into the Raspberry Pi and run:
sudo systemctl start turntable-stream
```

Or if not set up as a service:
```bash
cd /root/turntable-airplay-sender
python3 stream_server_v2.py
```

### "I don't see Turntable in my Sonos app"

You need to do the **one-time setup** (see below).

---

## One-Time Setup for Family Members

Only needs to be done ONCE per household:

### Step 1: Add TuneIn (if not already added)

1. Open Sonos app
2. Go to **Settings → Services & Voice**
3. Tap **Add a Service**
4. Find **TuneIn** and add it (it's free!)

### Step 2: Add Turntable Station

1. In Sonos app, go to **Browse → TuneIn**
2. Scroll to **My Radio Stations**
3. Tap the **three dots (⋯)** or settings icon
4. Select **Add New Radio Station**
5. Enter:
   - **Name:** `Turntable`
   - **URL:** `http://10.0.0.30:8000/turntable.mp3` (ask admin for correct IP)
6. Save!

✅ Done! "Turntable" will now always be in: **Browse → TuneIn → My Radio Stations**

### Step 3: Optional - Add to Favorites

1. Play "Turntable" once
2. Tap the **♡ heart icon**
3. Now it's in your **Favorites** for even easier access!

---

## What You're Listening To

- **Source:** USB turntable connected to Raspberry Pi
- **Quality:** MP3 320kbps, 48kHz stereo (CD quality)
- **Latency:** ~2-5 seconds (normal for streaming)
- **Range:** Works anywhere on your WiFi network

---

## For the Tech-Savvy

### Check Stream Status

Open a browser and go to: `http://10.0.0.30:8000/turntable.mp3`

You should hear the turntable audio (or be prompted to download). If you get an error, the stream isn't running.

### Start Stream Manually

SSH into the Raspberry Pi:
```bash
cd /root/turntable-airplay-sender
source venv/bin/activate
python3 stream_server_v2.py
```

### Control from Command Line

You can also play directly from SSH:
```bash
python3 play_on_sonos.py "Living Room"
```

---

## Enjoy Your Wireless Vinyl! 🎶

Questions? Ask the person who set this up!

