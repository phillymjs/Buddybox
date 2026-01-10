#!/usr/bin/env python3
import os
import subprocess
import json
import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configuration
WEB_DIR = "/var/www/html"
LAST_SYNC_FILE = os.path.join(WEB_DIR, "lastsync")
REMOVALS_LOG = "/home/administrator/removals.txt"
FIXTAGS_LOG = "/home/administrator/fixtags.txt"
MUSIC_DIR = "/mnt/music"
PLAYLIST_PATH = os.path.join(MUSIC_DIR, "playlist")
PORT = 80

class State:
    current_file = None
    metadata = ["", "", "", ""] # [Artist, Title, Album, Year]
    total_count = "0"
    track_index = "0"
    is_paused = False
    
class MplayerHandler(SimpleHTTPRequestHandler):
    
    def get_current_file_path(self):
        try:
            pid_cmd = ["pidof", "mplayer"]
            pid = subprocess.check_output(pid_cmd).decode().strip()
            fd_path = f"/proc/{pid}/fd/"
            for fd in os.listdir(fd_path):
                full_fd = os.path.join(fd_path, fd)
                try:
                    target = os.readlink(full_fd)
                    if target.startswith(MUSIC_DIR) and (target.endswith(".mp3") or target.endswith(".m4a")):
                        return target
                except:
                    continue
            return None
        except:
            return None
        
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
        if path == State.current_file and State.metadata:
            return 
        
        State.current_file = path
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
            
            # Comprehensive Year Check
            year_val = (
                tags.get("date") or 
                tags.get("DATE") or 
                tags.get("TYER") or 
                tags.get("TDRC") or 
                tags.get("original_date") or 
                tags.get("©day") or 
                ""
            )
            year = str(year_val).strip()[:4] if year_val else ""
            
            State.metadata = [artist, title, album, year]
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
        
    def do_GET(self):
        clean_path = self.path.split('?')[0]
        
        # --- API: Status Update ---
        if clean_path == '/api/status':
            path = self.get_current_file_path()
            if not path:
                State.current_file = None
                response = {
                    "lines": ["Not Playing", "", "", ""], 
                    "stats": "", 
                    "playlist_time": self.get_playlist_time(),
                    "paused": State.is_paused
                }
            else:
                self.update_metadata(path)
                self.update_counts(path)
                response = {
                    "lines": State.metadata,
                    "stats": f"Track {State.track_index} of {State.total_count}",
                    "playlist_time": self.get_playlist_time(),
                    "paused": State.is_paused
                }
                
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return
        
        # --- API: Fade Out ---
        elif clean_path == '/fade-out':
            if not State.is_paused:
                subprocess.Popen(["/usr/local/bin/fade-out"])
                State.is_paused = True
            self.send_response(200)
            self.end_headers()
            return
            
        # --- API: Fade In ---
        elif clean_path == '/fade-in':
            if State.is_paused:
                subprocess.Popen(["/usr/local/bin/fade-in"])
                State.is_paused = False
            self.send_response(200)
            self.end_headers()
            return

        # --- Standard Controls ---
        elif clean_path in ['/next', '/prev', '/pause']:
            if clean_path == '/pause':
                State.is_paused = not State.is_paused
            elif clean_path == '/next':
                State.is_paused = False # Assume playing if we skip
            
            subprocess.run([f"/usr/local/bin/{clean_path.strip('/')}"])
            self.send_response(200)
            self.end_headers()
            return
        
        # --- Sick/Fix Logging ---
        elif clean_path in ['/sick', '/fix']:
            log = REMOVALS_LOG if clean_path == '/sick' else FIXTAGS_LOG
            if State.current_file and len(State.metadata) >= 3:
                artist, title, album = State.metadata[0], State.metadata[1], State.metadata[2]
                log_entry = f"{artist} - {title} - {album}\n"
                with open(log, "a") as l:
                    l.write(log_entry)
            
            if clean_path == '/sick':
                State.is_paused = False
                subprocess.run(["/usr/local/bin/next"])
                
            self.send_response(200)
            self.end_headers()
            return
        
        elif clean_path == '/lastsync':
            content = "Unknown"
            if os.path.exists(LAST_SYNC_FILE):
                with open(LAST_SYNC_FILE, "r") as f: content = f.read().strip()
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(content.encode())
            return
            
        # Fallback to serving files (index.html, etc.)
        return super().do_GET()
        
if __name__ == '__main__':
    os.makedirs(WEB_DIR, exist_ok=True)
    os.chdir(WEB_DIR)
    server = HTTPServer(('0.0.0.0', PORT), MplayerHandler)
    print(f"Music Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()