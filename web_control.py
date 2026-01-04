#!/usr/bin/env python3
"""
Simple web interface for family to control turntable streaming.
No subscriptions, no apps - just open a webpage!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import soco
import socket
import logging
import json
import yaml
from pathlib import Path
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import time
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config file paths to check (in order)
CONFIG_PATHS = [
    Path('/opt/turntable-streaming/config.yaml'),
    Path('config.yaml'),
]

def get_config_path():
    """Find the config file."""
    for path in CONFIG_PATHS:
        if path.exists():
            return path
    return CONFIG_PATHS[0]  # Default to first path

def load_config():
    """Load configuration from YAML file."""
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def save_config(config):
    """Save configuration to YAML file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Config saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

STREAM_URL = f"http://{get_local_ip()}:8000/turntable.mp3"

# Speaker discovery cache to prevent repeated slow network scans
_speaker_cache = {'speakers': None, 'timestamp': 0}
_speaker_info_cache = {}  # Cache per-speaker info
_cache_duration = 15  # seconds (increased to reduce network load)

def invalidate_speaker_cache():
    """Clear speaker info cache to force fresh queries (called after play/stop)."""
    global _speaker_info_cache
    _speaker_info_cache.clear()
    logger.info("🗑️  Speaker info cache invalidated (forcing fresh queries)")

def discover_speakers_with_timeout(timeout=5):
    """
    Discover Sonos speakers with timeout to prevent hanging.
    Uses caching to avoid repeated slow network scans.
    """
    global _speaker_cache
    
    # Return cached speakers if still fresh
    now = time.time()
    if _speaker_cache['speakers'] is not None and (now - _speaker_cache['timestamp']) < _cache_duration:
        logger.debug(f"Using cached speakers ({len(_speaker_cache['speakers'])} found)")
        return _speaker_cache['speakers']
    
    logger.debug(f"Discovering speakers (timeout={timeout}s)...")
    
    def _discover():
        discovered = soco.discover()
        return list(discovered) if discovered else []
    
    # Run discovery with timeout
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_discover)
    
    try:
        speakers = future.result(timeout=timeout)
        _speaker_cache['speakers'] = speakers
        _speaker_cache['timestamp'] = now
        logger.info(f"Discovery completed: {len(speakers)} speaker(s) found")
        return speakers
    except FuturesTimeoutError:
        logger.warning(f"Speaker discovery timed out after {timeout}s - network may be slow")
        # Return cached speakers if available, otherwise empty list
        return _speaker_cache['speakers'] if _speaker_cache['speakers'] is not None else []
    except Exception as e:
        logger.error(f"Speaker discovery error: {e}")
        return _speaker_cache['speakers'] if _speaker_cache['speakers'] is not None else []
    finally:
        executor.shutdown(wait=False)

def get_speaker_info_with_timeout(speaker, timeout=8):
    """
    Get speaker info with timeout to prevent hanging on individual speaker queries.
    Uses per-speaker caching to reduce network load.
    Returns dict with speaker info or minimal info on timeout/error.
    """
    global _speaker_info_cache
    
    # Check cache first
    cache_key = speaker.player_name
    now = time.time()
    if cache_key in _speaker_info_cache:
        cached_data, cached_time = _speaker_info_cache[cache_key]
        cache_age = now - cached_time
        if cache_age < _cache_duration:
            logger.info(f"📦 Using cached info for {speaker.player_name} (age: {cache_age:.1f}s)")
            return cached_data
        else:
            logger.info(f"🔄 Cache expired for {speaker.player_name} (age: {cache_age:.1f}s), fetching fresh")
    else:
        logger.info(f"🆕 No cache for {speaker.player_name}, fetching fresh")
    
    def _get_info():
        is_playing = False
        is_coordinator = False
        coordinator_name = None
        model = 'Sonos'
        
        try:
            # Get basic info (combine to reduce calls)
            transport_info = speaker.get_current_transport_info()
            current_state = transport_info.get('current_transport_state', 'STOPPED')
            
            # Only get track info if playing (saves a network call for idle speakers)
            current_uri = ''
            if current_state == 'PLAYING':
                track_info = speaker.get_current_track_info()
                current_uri = track_info.get('uri', '')
                if 'turntable.mp3' in current_uri or ':8000' in current_uri:
                    is_playing = True
            
            # Log what we're seeing from Sonos
            logger.info(f"Speaker {speaker.player_name}: state={current_state}, uri={current_uri[:50] if current_uri else 'none'}, is_playing={is_playing}")
            
            # Check group membership
            try:
                coordinator = speaker.group.coordinator
                if coordinator == speaker:
                    is_coordinator = True
                else:
                    coordinator_name = coordinator.player_name
                    
                    # Check if grouped with coordinator playing turntable
                    if not is_playing and current_state == 'PLAYING':
                        # If this speaker is playing but not turntable, check coordinator
                        try:
                            coord_track = coordinator.get_current_track_info()
                            coord_uri = coord_track.get('uri', '')
                            if 'turntable.mp3' in coord_uri or ':8000' in coord_uri:
                                is_playing = True
                        except:
                            pass
            except:
                is_coordinator = True  # Assume coordinator if we can't determine
            
            # Get model (cache-friendly, rarely changes)
            try:
                model = speaker.get_speaker_info().get('model_name', 'Sonos')
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error getting speaker state for {speaker.player_name}: {e}")
        
        result = {
            'name': speaker.player_name,
            'model': model,
            'ip': speaker.ip_address,
            'playing': is_playing,
            'is_coordinator': is_coordinator,
            'coordinator_name': coordinator_name
        }
        
        # Cache the result
        _speaker_info_cache[cache_key] = (result, time.time())
        logger.info(f"✅ Fresh data for {speaker.player_name}: playing={is_playing}")
        
        return result
    
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_get_info)
    
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError:
        logger.warning(f"Timeout getting info for {speaker.player_name} after {timeout}s")
        # Return cached data if available
        if cache_key in _speaker_info_cache:
            cached_data, _ = _speaker_info_cache[cache_key]
            logger.info(f"Returning stale cache for {speaker.player_name}")
            return cached_data
        return {
            'name': speaker.player_name,
            'model': 'Sonos',
            'ip': speaker.ip_address,
            'playing': False,
            'is_coordinator': True,
            'coordinator_name': None
        }
    except Exception as e:
        logger.warning(f"Error getting info for {speaker.player_name}: {e}")
        if cache_key in _speaker_info_cache:
            cached_data, _ = _speaker_info_cache[cache_key]
            return cached_data
        return {
            'name': speaker.player_name,
            'model': 'Sonos',
            'ip': speaker.ip_address,
            'playing': False,
            'is_coordinator': True,
            'coordinator_name': None
        }
    finally:
        executor.shutdown(wait=False)

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Log HTTP requests."""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        # Parse path to strip query parameters (e.g., ?_t=timestamp for cache-busting)
        parsed_path = urlparse(self.path).path
        
        if parsed_path == '/settings':
            self.send_settings_page()
        elif parsed_path == '/api/config':
            self.send_config()
        elif parsed_path == '/api/restart':
            self.restart_service()
        elif parsed_path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Turntable Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        .emoji {{
            font-size: 4em;
            text-align: center;
            margin: 20px 0;
        }}
        .speaker {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
        }}
        .speaker.playing {{
            border-left: 4px solid #1DB954;
        }}
        .speaker.grouped {{
            margin-left: 30px;
            margin-top: 5px;
            margin-bottom: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .coordinator-badge {{
            display: inline-block;
            background: #1DB954;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 8px;
            font-weight: bold;
        }}
        .status-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
            background: #ccc;
        }}
        .status-indicator.playing {{
            background: #1DB954;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .status-text {{
            font-size: 12px;
            color: #1DB954;
            font-weight: bold;
            margin-left: 5px;
        }}
        button {{
            background: #1DB954;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            font-weight: bold;
        }}
        button:hover {{
            background: #1ed760;
        }}
        button:active {{
            background: #1aa34a;
        }}
        button.stop-btn {{
            background: #dc3545;
        }}
        button.stop-btn:hover {{
            background: #c82333;
        }}
        button.stop-btn:active {{
            background: #bd2130;
        }}
        .info {{
            background: white;
            padding: 15px;
            margin: 20px 0;
            border-radius: 10px;
            border-left: 4px solid #1DB954;
        }}
        .loading {{
            text-align: center;
            color: #666;
            margin: 20px 0;
        }}
        .btn-spinner {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 5px;
            vertical-align: middle;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        button:disabled {{
            opacity: 0.7;
            cursor: not-allowed;
        }}
    </style>
</head>
<body>
    <div class="emoji">🎵</div>
    <h1>Turntable Control</h1>
    
    <div class="info">
        <strong>Stream URL:</strong><br>
        <a href="{STREAM_URL}" target="_blank">{STREAM_URL}</a>
        <div style="margin-top: 10px;">
            <a href="/settings" style="color: #1DB954; text-decoration: none; font-weight: bold;">⚙️ Settings</a>
        </div>
    </div>
    
    <div id="speakers">
        <div class="loading">Finding Sonos speakers...</div>
    </div>
    
    <script>
        async function loadSpeakers(forceRefresh = false) {{
            console.log('[LoadSpeakers] Called with forceRefresh:', forceRefresh);
            try {{
                // Add cache-busting parameter for forced refreshes
                const url = forceRefresh 
                    ? `/api/speakers?_t=${{Date.now()}}` 
                    : '/api/speakers';
                console.log('[LoadSpeakers] Fetching:', url);
                const response = await fetch(url);
                const speakers = await response.json();
                console.log('[LoadSpeakers] Got', speakers.length, 'speakers');
                
                const container = document.getElementById('speakers');
                container.innerHTML = '';
                
                if (speakers.length === 0) {{
                    container.innerHTML = '<div class="info">No Sonos speakers found</div>';
                    return;
                }}
                
                // Sort speakers: coordinators first, then their grouped members
                const sortedSpeakers = [];
                const coordinators = speakers.filter(s => s.is_coordinator);
                const members = speakers.filter(s => !s.is_coordinator);
                
                coordinators.forEach(coordinator => {{
                    sortedSpeakers.push(coordinator);
                    // Add grouped members right after their coordinator
                    const groupedMembers = members.filter(m => m.coordinator_name === coordinator.name);
                    sortedSpeakers.push(...groupedMembers);
                }});
                
                // Add any ungrouped non-coordinator speakers (shouldn't happen, but just in case)
                const orphans = members.filter(m => !sortedSpeakers.includes(m));
                sortedSpeakers.push(...orphans);
                
                sortedSpeakers.forEach(speaker => {{
                    console.log('[LoadSpeakers] Rendering speaker:', speaker.name, 'playing:', speaker.playing);
                    const div = document.createElement('div');
                    let className = speaker.playing ? 'speaker playing' : 'speaker';
                    if (!speaker.is_coordinator && speaker.coordinator_name) {{
                        className += ' grouped';
                    }}
                    div.className = className;
                    
                    const buttonAction = speaker.playing ? 'stop' : 'play';
                    const buttonText = speaker.playing ? 'Stop' : 'Play';
                    const buttonClass = speaker.playing ? 'stop-btn' : '';
                    const buttonId = `btn-${{speaker.name.replace(/\s+/g, '-')}}`;
                    
                    console.log('[LoadSpeakers]   Button:', buttonText, 'Action:', buttonAction, 'ID:', buttonId);
                    
                    const coordinatorBadge = speaker.is_coordinator && speaker.playing 
                        ? '<span class="coordinator-badge">GROUP</span>' 
                        : '';
                    
                    div.innerHTML = `
                        <div>
                            <span class="status-indicator ${{speaker.playing ? 'playing' : ''}}"></span>
                            <strong>${{speaker.name}}</strong>
                            ${{coordinatorBadge}}
                            ${{speaker.playing ? '<span class="status-text">Playing</span>' : ''}}
                            <br>
                            <small>${{speaker.model}}</small>
                        </div>
                        <button id="${{buttonId}}" class="${{buttonClass}}" onclick="${{buttonAction}}('${{speaker.name}}')">${{buttonText}}</button>
                    `;
                    container.appendChild(div);
                }});
            }} catch (e) {{
                document.getElementById('speakers').innerHTML = 
                    '<div class="info">Error loading speakers</div>';
            }}
        }}
        
        async function play(speakerName) {{
            const buttonId = `btn-${{speakerName.replace(/\s+/g, '-')}}`;
            const button = document.getElementById(buttonId);
            
            console.log('[Play] Starting for:', speakerName, 'Button ID:', buttonId, 'Found:', !!button);
            
            if (!button) {{
                console.error('[Play] Button not found!', buttonId);
                return;
            }}
            
            const originalText = button.textContent;
            
            try {{
                // Show loading on button
                button.disabled = true;
                button.innerHTML = '<span class="btn-spinner"></span>Starting...';
                console.log('[Play] API call starting...');
                
                const response = await fetch('/api/play', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{speaker: speakerName}})
                }});
                
                const result = await response.json();
                console.log('[Play] API result:', result);
                
                if (result.success) {{
                    // Pause automatic refresh to avoid showing stale data during wait
                    pauseAutoRefresh();
                    
                    // Wait longer for Play (TRANSITIONING → PLAYING takes time)
                    button.innerHTML = '<span class="btn-spinner"></span>Connecting...';
                    console.log('[Play] Waiting 6 seconds for TRANSITIONING→PLAYING...');
                    await new Promise(resolve => setTimeout(resolve, 6000));
                    
                    // Force refresh speaker list (bypass cache)
                    // Note: This rebuilds the entire speaker list with new buttons
                    console.log('[Play] Force refreshing speaker list...');
                    await loadSpeakers(true);
                    console.log('[Play] Complete! Speaker list rebuilt with updated state.');
                    
                    // Restart automatic refresh
                    startAutoRefresh();
                    // Don't touch button after this - it's been replaced by loadSpeakers()
                }} else {{
                    button.disabled = false;
                    button.textContent = originalText;
                    alert('❌ Error: ' + result.error);
                }}
            }} catch (e) {{
                console.error('[Play] Error:', e);
                button.disabled = false;
                button.textContent = originalText;
                alert('❌ Error starting playback: ' + e.message);
            }}
        }}
        
        async function stop(speakerName) {{
            const buttonId = `btn-${{speakerName.replace(/\s+/g, '-')}}`;
            const button = document.getElementById(buttonId);
            
            if (!button) return;
            
            const originalText = button.textContent;
            
            try {{
                // Show loading on button
                button.disabled = true;
                button.innerHTML = '<span class="btn-spinner"></span>Stopping...';
                
                const response = await fetch('/api/stop', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{speaker: speakerName}})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    // Pause automatic refresh to avoid showing stale data during wait
                    pauseAutoRefresh();
                    
                    // Wait a moment for Sonos to update its state
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    // Force refresh speaker list (bypass cache)
                    await loadSpeakers(true);
                    
                    // Restart automatic refresh
                    startAutoRefresh();
                }} else {{
                    button.disabled = false;
                    button.textContent = originalText;
                    alert('❌ Error: ' + result.error);
                }}
            }} catch (e) {{
                button.disabled = false;
                button.textContent = originalText;
                alert('❌ Error stopping playback');
            }}
        }}
        
        // Track the auto-refresh interval so we can pause it during actions
        let autoRefreshInterval = null;
        
        function startAutoRefresh() {{
            // Clear any existing interval
            if (autoRefreshInterval) {{
                clearInterval(autoRefreshInterval);
            }}
            // Refresh speaker status every 20 seconds (matches server cache)
            autoRefreshInterval = setInterval(loadSpeakers, 20000);
        }}
        
        function pauseAutoRefresh() {{
            if (autoRefreshInterval) {{
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }}
        }}
        
        // Load speakers immediately
        loadSpeakers();
        
        // Start auto-refresh
        startAutoRefresh();
    </script>
</body>
</html>
            """
            
            self.wfile.write(html.encode())
            
        elif parsed_path == '/api/speakers':
            # Check if this is a forced refresh (from user action)
            from urllib.parse import parse_qs
            query_params = parse_qs(urlparse(self.path).query)
            force_refresh = '_t' in query_params  # Cache-busting timestamp means forced refresh
            
            if force_refresh:
                logger.info("API: 🔄 Forced refresh requested, clearing cache first")
                invalidate_speaker_cache()
            else:
                logger.info("API: Discovering Sonos speakers...")
            
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                speakers = discover_speakers_with_timeout(timeout=5)
                
                # Query all speakers in parallel for speed (with caching)
                speaker_list = []
                if speakers:
                    logger.info(f"API: Querying {len(speakers)} speakers in parallel...")
                    with ThreadPoolExecutor(max_workers=min(len(speakers), 10)) as executor:
                        futures = [(s.player_name, executor.submit(get_speaker_info_with_timeout, s, 8)) for s in speakers]
                        for speaker_name, future in futures:
                            try:
                                speaker_info = future.result(timeout=10)  # Overall timeout per speaker
                                speaker_list.append(speaker_info)
                                logger.info(f"API: ✅ Got info for {speaker_name}: playing={speaker_info.get('playing')}")
                            except Exception as e:
                                logger.error(f"API: ❌ Failed to get speaker info for {speaker_name}: {e}", exc_info=True)
                
                # Log the actual speaker names and playing status being sent
                speaker_summary = ', '.join([f"{s['name']}={'▶' if s['playing'] else '⏸'}" for s in speaker_list])
                logger.info(f"API: Returning {len(speaker_list)} speakers: {speaker_summary}")
                
                response = json.dumps(speaker_list)
                try:
                    self.wfile.write(response.encode())
                    logger.info(f"API: ✅ Response sent successfully")
                except BrokenPipeError:
                    logger.warning("API: Client disconnected before response could be sent (timeout)")
                except Exception as e:
                    logger.error(f"API: Error sending response: {e}")
            except BrokenPipeError:
                logger.warning("API: Client disconnected during /api/speakers (BrokenPipe)")
            except Exception as e:
                logger.error(f"API: Error in /api/speakers: {e}", exc_info=True)
                try:
                    self.send_error(500, f"Internal error: {e}")
                except (BrokenPipeError, ConnectionResetError):
                    logger.warning("API: Could not send error response, client already disconnected")
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_stop(self):
        """Stop playback on a speaker."""
        logger.info("API: Received stop request")
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode())
            speaker_name = data.get('speaker')
            logger.info(f"API: Request to stop speaker: {speaker_name}")
            
            logger.info("API: Discovering speakers...")
            speakers = discover_speakers_with_timeout(timeout=5)
            
            target = None
            for s in speakers:
                logger.debug(f"API: Checking speaker: {s.player_name}")
                if speaker_name.lower() in s.player_name.lower():
                    target = s
                    logger.info(f"API: Matched speaker: {s.player_name}")
                    break
            
            if target:
                # Check if this speaker is the coordinator or a grouped member
                try:
                    coordinator = target.group.coordinator
                    if coordinator == target:
                        # This is the coordinator - stop entire group
                        logger.info(f"API: Stopping coordinator {target.player_name} (stops entire group)")
                        target.stop()
                    else:
                        # This is a grouped member - just remove from group
                        logger.info(f"API: Removing {target.player_name} from group with {coordinator.player_name}")
                        target.unjoin()
                except Exception as e:
                    # Fallback: just stop
                    logger.warning(f"API: Could not determine group status, stopping: {e}")
                    target.stop()
                
                # Invalidate cache for immediate UI update
                invalidate_speaker_cache()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
                logger.info(f"API: ✅ Successfully stopped playback on {target.player_name}")
            else:
                error_msg = f"Speaker '{speaker_name}' not found"
                logger.error(f"API: {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"API: ❌ Error in /api/stop: {e}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/config':
            self.save_config_handler()
        elif self.path == '/api/stop':
            self.handle_stop()
        elif self.path == '/api/play':
            logger.info("API: Received play request")
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                data = json.loads(post_data.decode())
                speaker_name = data.get('speaker')
                logger.info(f"API: Request to play on speaker: {speaker_name}")
                
                logger.info("API: Discovering speakers...")
                speakers = discover_speakers_with_timeout(timeout=5)
                
                target = None
                for s in speakers:
                    logger.debug(f"API: Checking speaker: {s.player_name}")
                    if speaker_name.lower() in s.player_name.lower():
                        target = s
                        logger.info(f"API: Matched speaker: {s.player_name}")
                        break
                
                if target:
                    # Check if any other speakers are already playing the turntable stream
                    playing_coordinator = None
                    for s in speakers:
                        try:
                            transport_info = s.get_current_transport_info()
                            track_info = s.get_current_track_info()
                            if transport_info.get('current_transport_state') == 'PLAYING':
                                current_uri = track_info.get('uri', '')
                                if 'turntable.mp3' in current_uri or ':8000' in current_uri:
                                    # Found a speaker playing turntable - use its coordinator
                                    playing_coordinator = s.group.coordinator
                                    logger.info(f"API: Found existing playback on {playing_coordinator.player_name}")
                                    break
                        except:
                            pass
                    
                    if playing_coordinator and playing_coordinator != target:
                        # Join existing group
                        logger.info(f"API: Joining {target.player_name} to group with {playing_coordinator.player_name}")
                        target.join(playing_coordinator)
                        
                        # Invalidate cache for immediate UI update
                        invalidate_speaker_cache()
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                        logger.info(f"API: ✅ Successfully joined {target.player_name} to group")
                    else:
                        # Start fresh playback (no one else playing turntable)
                        # Only stop if we're the coordinator or ungrouped
                        try:
                            if target.group.coordinator == target:
                                logger.info(f"API: Stopping current playback on {target.player_name} (coordinator)")
                                target.stop()
                            else:
                                logger.info(f"API: Unjoining {target.player_name} from group")
                                target.unjoin()
                        except:
                            pass
                        
                        logger.info(f"API: Clearing queue on {target.player_name}")
                        target.clear_queue()
                        
                        logger.info(f"API: Playing stream: {STREAM_URL}")
                        target.play_uri(STREAM_URL, title="Turntable")
                        
                        # Invalidate cache for immediate UI update
                        invalidate_speaker_cache()
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                        logger.info(f"API: ✅ Successfully started playback on {target.player_name}")
                else:
                    error_msg = f"Speaker '{speaker_name}' not found"
                    logger.error(f"API: {error_msg}")
                    raise Exception(error_msg)
                    
            except Exception as e:
                logger.error(f"API: ❌ Error in /api/play: {e}", exc_info=True)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_config(self):
        """Send current configuration as JSON."""
        try:
            config = load_config()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config).encode())
            logger.info("API: Sent current config")
        except Exception as e:
            logger.error(f"Error sending config: {e}")
            self.send_response(500)
            self.end_headers()
    
    def save_config_handler(self):
        """Save configuration from POST request."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_config = json.loads(post_data.decode())
            
            logger.info(f"API: Saving config changes")
            success = save_config(new_config)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'success': success,
                'message': 'Config saved. Restart stream_server_v2.py to apply changes.' if success else 'Failed to save config'
            }
            self.wfile.write(json.dumps(response).encode())
            
            if success:
                logger.info("API: ✅ Config saved successfully")
            else:
                logger.error("API: ❌ Failed to save config")
                
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
    
    def restart_service(self):
        """Restart the turntable-stream systemd service."""
        try:
            logger.info("API: Attempting to restart turntable-stream service")
            
            # Check if running as root
            is_root = os.geteuid() == 0
            
            # Build command - skip sudo if already root
            if is_root:
                cmd = ['systemctl', 'restart', 'turntable-stream']
                logger.info("Running as root, skipping sudo")
            else:
                cmd = ['sudo', 'systemctl', 'restart', 'turntable-stream']
                logger.info("Running as user, using sudo")
            
            # Try to restart the service
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if result.returncode == 0:
                logger.info("API: ✅ Service restarted successfully")
                response = {
                    'success': True,
                    'message': 'Streaming server restarted successfully! Changes applied.'
                }
            else:
                logger.error(f"API: ❌ Service restart failed: {result.stderr}")
                response = {
                    'success': False,
                    'message': f'Restart failed. You may need to configure sudo permissions. Error: {result.stderr}'
                }
            
            self.wfile.write(json.dumps(response).encode())
            
        except subprocess.TimeoutExpired:
            logger.error("API: Service restart timed out")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': 'Restart timed out'
            }).encode())
        except Exception as e:
            logger.error(f"API: Error restarting service: {e}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': f'Error: {str(e)}'
            }).encode())
    
    def send_settings_page(self):
        """Send the settings page HTML."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Turntable Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 700px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .section h2 {
            margin-top: 0;
            color: #1DB954;
            font-size: 1.2em;
        }
        .field {
            margin: 15px 0;
        }
        .field label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
            color: #333;
        }
        .field small {
            display: block;
            color: #666;
            margin-top: 3px;
        }
        input[type="text"], input[type="number"], select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
            font-size: 16px;
        }
        .checkbox-field {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-field input[type="checkbox"] {
            width: 20px;
            height: 20px;
        }
        button {
            background: #1DB954;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            font-weight: bold;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            background: #1ed760;
        }
        button:active {
            background: #1aa34a;
        }
        button.secondary {
            background: #666;
        }
        button.secondary:hover {
            background: #777;
        }
        button.secondary:active {
            background: #555;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .back-link {
            display: block;
            text-align: center;
            margin: 20px 0;
            color: #1DB954;
            text-decoration: none;
            font-weight: bold;
        }
        .alert {
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            display: none;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            text-align: center;
            color: #666;
            padding: 20px;
        }
    </style>
</head>
<body>
    <h1>⚙️ Settings</h1>
    
    <div id="loading" class="loading">Loading settings...</div>
    <div id="alert" class="alert"></div>
    
    <form id="settingsForm" style="display:none;">
        <div class="section">
            <h2>🎵 Auto-Play Detection</h2>
            
            <div class="field checkbox-field">
                <input type="checkbox" id="autoplay_enabled" name="auto_play.enabled">
                <label for="autoplay_enabled">Enable Auto-Play (power-on + needle-drop detection)</label>
            </div>
            
            <div class="field">
                <label for="default_speaker">Default Speaker</label>
                <input type="text" id="default_speaker" name="auto_play.default_speaker" placeholder="Living Room">
                <small>Which Sonos speaker to auto-start</small>
            </div>
            
            <div class="field">
                <label for="power_on_threshold">Power-On Threshold</label>
                <input type="number" id="power_on_threshold" name="auto_play.power_on_threshold" min="1000" max="30000" step="1000">
                <small>RMS level for turntable power-on spike (15000-25000 typical)</small>
            </div>
            
            <div class="field">
                <label for="audio_threshold">Needle-Drop Threshold</label>
                <input type="number" id="audio_threshold" name="auto_play.audio_threshold" min="100" max="2000" step="50">
                <small>RMS level for normal music (300-1000 recommended)</small>
            </div>
            
            <div class="field">
                <label for="trigger_delay">Trigger Delay (seconds)</label>
                <input type="number" id="trigger_delay" name="auto_play.trigger_delay" min="1" max="10" step="0.5">
                <small>How long audio must sustain before triggering</small>
            </div>
            
            <div class="field">
                <label for="power_on_cooldown">Power-On Cooldown (seconds)</label>
                <input type="number" id="power_on_cooldown" name="auto_play.power_on_cooldown" min="10" max="60" step="5">
                <small>Time to drop needle after power-on (prevents re-trigger)</small>
            </div>
            
            <div class="field">
                <label for="reset_disconnect">Reset After Disconnect (seconds)</label>
                <input type="number" id="reset_disconnect" name="auto_play.reset_on_disconnect_delay" min="5" max="30" step="5">
                <small>Reset trigger when no clients for this long (switched to TV)</small>
            </div>
        </div>
        
        <div class="section">
            <h2>🔊 Audio Processing</h2>
            
            <div class="field">
                <label for="volume_gain">Volume Gain</label>
                <input type="number" id="volume_gain" name="audio_processing.volume_gain" min="0.5" max="5" step="0.5">
                <small>Volume boost multiplier (1.0 = normal, 2.0 = double, 3.0 = triple)</small>
            </div>
        </div>
        
        <button type="submit">💾 Save Settings</button>
        <button type="button" class="secondary" id="restartBtn" onclick="restartServer()">🔄 Restart Streaming Server</button>
        <a href="/" class="back-link">← Back to Control</a>
    </form>
    
    <script>
        async function loadSettings() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                
                // Populate form fields
                document.getElementById('autoplay_enabled').checked = config.auto_play?.enabled || false;
                document.getElementById('default_speaker').value = config.auto_play?.default_speaker || 'Living Room';
                document.getElementById('power_on_threshold').value = config.auto_play?.power_on_threshold || 15000;
                document.getElementById('audio_threshold').value = config.auto_play?.audio_threshold || 500;
                document.getElementById('trigger_delay').value = config.auto_play?.trigger_delay || 2.0;
                document.getElementById('power_on_cooldown').value = config.auto_play?.power_on_cooldown || 30;
                document.getElementById('reset_disconnect').value = config.auto_play?.reset_on_disconnect_delay || 10;
                document.getElementById('volume_gain').value = config.audio_processing?.volume_gain || 2.0;
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('settingsForm').style.display = 'block';
            } catch (e) {
                document.getElementById('loading').textContent = 'Error loading settings';
            }
        }
        
        document.getElementById('settingsForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Build config object from form
            const config = {
                auto_play: {
                    enabled: document.getElementById('autoplay_enabled').checked,
                    default_speaker: document.getElementById('default_speaker').value,
                    power_on_threshold: parseInt(document.getElementById('power_on_threshold').value),
                    audio_threshold: parseInt(document.getElementById('audio_threshold').value),
                    trigger_delay: parseFloat(document.getElementById('trigger_delay').value),
                    power_on_cooldown: parseInt(document.getElementById('power_on_cooldown').value),
                    reset_on_disconnect_delay: parseInt(document.getElementById('reset_disconnect').value)
                },
                audio_processing: {
                    volume_gain: parseFloat(document.getElementById('volume_gain').value)
                }
            };
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                
                const result = await response.json();
                const alert = document.getElementById('alert');
                
                if (result.success) {
                    alert.className = 'alert alert-success';
                    alert.textContent = '✅ Settings saved! Restart the streaming server to apply changes.';
                } else {
                    alert.className = 'alert alert-error';
                    alert.textContent = '❌ Error: ' + result.message;
                }
                
                alert.style.display = 'block';
                window.scrollTo(0, 0);
                
                // Hide alert after 5 seconds
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 5000);
            } catch (e) {
                const alert = document.getElementById('alert');
                alert.className = 'alert alert-error';
                alert.textContent = '❌ Error saving settings';
                alert.style.display = 'block';
            }
        });
        
        async function restartServer() {
            if (!confirm('Restart the streaming server? This will briefly interrupt any active playback.')) {
                return;
            }
            
            const btn = document.getElementById('restartBtn');
            btn.disabled = true;
            btn.textContent = '⏳ Restarting...';
            
            try {
                const response = await fetch('/api/restart');
                const result = await response.json();
                
                const alert = document.getElementById('alert');
                
                if (result.success) {
                    alert.className = 'alert alert-success';
                    alert.textContent = '✅ ' + result.message;
                } else {
                    alert.className = 'alert alert-error';
                    alert.textContent = '❌ ' + result.message;
                }
                
                alert.style.display = 'block';
                window.scrollTo(0, 0);
                
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 5000);
            } catch (e) {
                const alert = document.getElementById('alert');
                alert.className = 'alert alert-error';
                alert.textContent = '❌ Error restarting server';
                alert.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 Restart Streaming Server';
            }
        }
        
        loadSettings();
    </script>
</body>
</html>
        """
        
        self.wfile.write(html.encode())

def main():
    PORT = 8080
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("🎵 Turntable Web Control")
    print("=" * 60)
    print(f"\n🌐 Open this on any device:")
    print(f"   http://{local_ip}:{PORT}")
    print(f"\n💡 Bookmark this on family phones/tablets!")
    print(f"\n⏹️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    server = HTTPServer(('0.0.0.0', PORT), WebHandler)
    logger.info(f"Web control server running on port {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()

