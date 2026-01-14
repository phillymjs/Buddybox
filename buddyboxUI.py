#!/usr/bin/env python3
import os
import subprocess
import json
import datetime
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configuration
WEB_DIR = "/var/www/html"
REMOVALS_LOG = "/home/administrator/removals.txt"
FIXTAGS_LOG = "/home/administrator/fixtags.txt"
MUSIC_DIR = "/mnt/music"
LAST_SYNC_FILE = os.path.join(MUSIC_DIR, ".lastsync")
PLAYLIST_PATH = os.path.join(MUSIC_DIR, "playlist")
MPV_SOCKET = "/tmp/mpv-socket"
PORT = 80

class State:
    current_file = None
    metadata = ["", "", "", ""] # [Artist, Title, Album, Year]
    total_count = "0"
    track_index = "0"
    is_paused = False
    
class MPVTracker(threading.Thread):
    def __init__(self, socket_path=MPV_SOCKET, output_file="/mnt/music/track"):
        super().__init__()
        self.socket_path = socket_path
        self.output_file = output_file
        self.daemon = True
        self.running = True
        
    def run(self):
        while self.running:
            if not os.path.exists(self.socket_path):
                threading.Event().wait(2)
                continue
            
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(self.socket_path)
                query = {"command": ["get_property", "playlist-pos"]}
                client.send(json.dumps(query).encode() + b'\n')
                
                while self.running:
                    data = client.recv(4096)
                    if not data: break
                    
                    for line in data.decode().splitlines():
                        try:
                            event = json.loads(line)
                            if event.get("event") == "start-file":
                                query = {"command": ["get_property", "playlist-pos"]}
                                client.send(json.dumps(query).encode() + b'\n')
                            
                            if "data" in event and isinstance(event["data"], int):
                                with open(self.output_file, "w") as f:
                                    f.write(str(event["data"]))
                        except json.JSONDecodeError:
                            continue
            except (socket.error, IOError):
                threading.Event().wait(2)
            finally:
                client.close()
    
class BuddyBoxHandler(SimpleHTTPRequestHandler):
    
    def get_mpv_status(self):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.connect(MPV_SOCKET)
                s.sendall(json.dumps({"command": ["get_property", "path"]}).encode() + b"\n")
                path_data = json.loads(s.recv(4096).decode().splitlines()[0])
                s.sendall(json.dumps({"command": ["get_property", "pause"]}).encode() + b"\n")
                pause_data = json.loads(s.recv(4096).decode().splitlines()[0])
                return path_data.get("data"), pause_data.get("data", False)
        except:
            return None, False

    def update_counts(self, path):
        try:
            if State.total_count == "0":
                find_cmd = ["find", MUSIC_DIR, "-type", "f", "(", "-iname", "*.mp3", "-o", "-iname", "*.m4a", ")", "!", "-path", "*/.*", "!", "-name", "._*"]
                find_out = subprocess.check_output(find_cmd)
                State.total_count = str(len(find_out.decode().splitlines()))
                
            if path:
                filename = os.path.basename(path)
                grep_cmd = ["grep", "-nF", filename, PLAYLIST_PATH]
                result = subprocess.check_output(grep_cmd).decode().strip()
                if result:
                    State.track_index = result.split(":")[0]
                else:
                    State.track_index = "0"
        except:
            State.track_index = "0"
            
    def update_metadata(self, path):
        norm_path = os.path.abspath(path) if path else None
        if norm_path == State.current_file and any(State.metadata):
            return 
        
        State.current_file = norm_path
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
            output = subprocess.check_output(cmd).decode()
            data = json.loads(output)
            tags = data.get("format", {}).get("tags", {})
            
            title = tags.get("title") or tags.get("TITLE") or tags.get("©nam")
            if not title:
                title = os.path.splitext(os.path.basename(path))[0]
                
            artist = tags.get("artist") or tags.get("ARTIST") or tags.get("©ART") or "Unknown Artist"
            album = tags.get("album") or tags.get("ALBUM") or tags.get("©alb") or ""
            
            year_val = (tags.get("date") or tags.get("DATE") or tags.get("TYER") or 
                        tags.get("TDRC") or tags.get("original_date") or tags.get("©day") or "")
            year = str(year_val).strip()[:4] if year_val else ""
            
            State.metadata = [str(artist), str(title), str(album), str(year)]
        except:
            State.metadata = ["Metadata Error", os.path.basename(path), "", ""]
            
    def get_playlist_time(self):
        try:
            if os.path.exists(PLAYLIST_PATH):
                mtime = os.path.getmtime(PLAYLIST_PATH)
                dt = datetime.datetime.fromtimestamp(mtime)
                return dt.strftime("%B %-d, %Y • %-I:%M %p")
            return "Unknown"
        except:
            return "Unknown"

    def get_lastsync_time(self):
        try:
            if os.path.exists(LAST_SYNC_FILE):
                mtime = os.path.getmtime(LAST_SYNC_FILE)
                dt = datetime.datetime.fromtimestamp(mtime)
                return dt.strftime("%B %-d, %Y • %-I:%M %p")
            return "Unknown"
        except:
            return "Unknown"
        
    def do_GET(self):
        clean_path = self.path.split('?')[0]
        
        if clean_path == '/api/status':
            path, is_paused = self.get_mpv_status()
            State.is_paused = is_paused
            
            if not path:
                State.current_file = None
                response = {
                    "lines": ["Not Playing", "", "", ""], 
                    "stats": "", 
                    "playlist_time": self.get_playlist_time(),
                    "lastsync_time": self.get_lastsync_time(),
                    "paused": True
                }
            else:
                self.update_metadata(path)
                self.update_counts(path)
                response = {
                    "lines": State.metadata,
                    "stats": f"Track {State.track_index} of {State.total_count}",
                    "playlist_time": self.get_playlist_time(),
                    "lastsync_time": self.get_lastsync_time(),
                    "paused": State.is_paused
                }
                
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return
        
        elif clean_path in ['/next', '/prev', '/pause']:
            subprocess.Popen([f"/usr/local/bin/bb-{clean_path.strip('/')}"])
            self.send_response(200)
            self.end_headers()
            return

        elif clean_path in ['/fade-out', '/fade-in']:
            direction = "out" if "fade-out" in clean_path else "in"
            query = self.path.split('?')
            duration = query[1] if len(query) > 1 and query[1].isdigit() else None
            cmd = ["/usr/local/bin/bb-fade", direction]
            if duration: cmd.append(duration)
            subprocess.Popen(cmd)
            self.send_response(200)
            self.end_headers()
            return
        
        elif clean_path in ['/sick', '/fix']:
            log = REMOVALS_LOG if clean_path == '/sick' else FIXTAGS_LOG
            if State.current_file and len(State.metadata) >= 3:
                log_entry = f"{State.metadata[0]} - {State.metadata[1]} - {State.metadata[2]}\n"
                with open(log, "a") as l: l.write(log_entry)
            
            if clean_path == '/sick':
                subprocess.run(["/usr/local/bin/bb-next"])
                
            self.send_response(200)
            self.end_headers()
            return
            
        return super().do_GET()
        
if __name__ == '__main__':
    tracker = MPVTracker()
    tracker.start()
    os.makedirs(WEB_DIR, exist_ok=True)
    os.chdir(WEB_DIR)
    server = HTTPServer(('0.0.0.0', PORT), BuddyBoxHandler)
    print(f"BuddyBox UI Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
