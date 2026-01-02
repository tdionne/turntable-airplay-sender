#!/usr/bin/env python3
"""
Simple web interface for family to control turntable streaming.
No subscriptions, no apps - just open a webpage!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import soco
import socket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

STREAM_URL = f"http://{get_local_ip()}:8000/turntable.mp3"

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Log HTTP requests."""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
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
    </style>
</head>
<body>
    <div class="emoji">🎵</div>
    <h1>Turntable Control</h1>
    
    <div class="info">
        <strong>Stream URL:</strong><br>
        <a href="{STREAM_URL}" target="_blank">{STREAM_URL}</a>
    </div>
    
    <div id="speakers">
        <div class="loading">Finding Sonos speakers...</div>
    </div>
    
    <script>
        async function loadSpeakers() {{
            try {{
                const response = await fetch('/api/speakers');
                const speakers = await response.json();
                
                const container = document.getElementById('speakers');
                container.innerHTML = '';
                
                if (speakers.length === 0) {{
                    container.innerHTML = '<div class="info">No Sonos speakers found</div>';
                    return;
                }}
                
                speakers.forEach(speaker => {{
                    const div = document.createElement('div');
                    div.className = 'speaker';
                    div.innerHTML = `
                        <div>
                            <strong>${{speaker.name}}</strong><br>
                            <small>${{speaker.model}}</small>
                        </div>
                        <button onclick="play('${{speaker.name}}')">Play</button>
                    `;
                    container.appendChild(div);
                }});
            }} catch (e) {{
                document.getElementById('speakers').innerHTML = 
                    '<div class="info">Error loading speakers</div>';
            }}
        }}
        
        async function play(speakerName) {{
            try {{
                const response = await fetch('/api/play', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{speaker: speakerName}})
                }});
                
                const result = await response.json();
                if (result.success) {{
                    alert('✅ Playing on ' + speakerName + '!\\n\\nPut a record on the turntable.');
                }} else {{
                    alert('❌ Error: ' + result.error);
                }}
            }} catch (e) {{
                alert('❌ Error starting playback');
            }}
        }}
        
        loadSpeakers();
    </script>
</body>
</html>
            """
            
            self.wfile.write(html.encode())
            
        elif self.path == '/api/speakers':
            logger.info("API: Discovering Sonos speakers...")
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                speakers = list(soco.discover()) or []
                logger.info(f"API: Found {len(speakers)} speaker(s)")
                
                speaker_list = []
                for s in speakers:
                    try:
                        speaker_info = {
                            'name': s.player_name,
                            'model': s.get_speaker_info().get('model_name', 'Sonos'),
                            'ip': s.ip_address
                        }
                        speaker_list.append(speaker_info)
                        logger.debug(f"API: Found speaker: {speaker_info['name']} at {speaker_info['ip']}")
                    except Exception as e:
                        logger.warning(f"API: Error getting speaker info: {e}")
                
                import json
                response = json.dumps(speaker_list)
                self.wfile.write(response.encode())
                logger.info(f"API: Returned {len(speaker_list)} speaker(s) to client")
            except Exception as e:
                logger.error(f"API: Error in /api/speakers: {e}", exc_info=True)
                self.send_error(500, f"Internal error: {e}")
            
        elif self.path == '/api/play':
            logger.info("API: Received play request")
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                import json
                data = json.loads(post_data.decode())
                speaker_name = data.get('speaker')
                logger.info(f"API: Request to play on speaker: {speaker_name}")
                
                logger.info("API: Discovering speakers...")
                speakers = list(soco.discover()) or []
                logger.info(f"API: Found {len(speakers)} speaker(s)")
                
                target = None
                for s in speakers:
                    logger.debug(f"API: Checking speaker: {s.player_name}")
                    if speaker_name.lower() in s.player_name.lower():
                        target = s
                        logger.info(f"API: Matched speaker: {s.player_name}")
                        break
                
                if target:
                    logger.info(f"API: Stopping current playback on {target.player_name}")
                    target.stop()
                    
                    logger.info(f"API: Clearing queue on {target.player_name}")
                    target.clear_queue()
                    
                    logger.info(f"API: Playing stream: {STREAM_URL}")
                    target.play_uri(STREAM_URL, title="Turntable")
                    
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

