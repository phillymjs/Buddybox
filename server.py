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
    metadata = []
    total_count = "0"
    track_index = "0"

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
            
            # 1. Look for Title tags
            title = tags.get("title") or tags.get("TITLE") or tags.get("©nam")
            
            # 2. Fallback: Use filename without the extension
            if not title:
                title = os.path.splitext(os.path.basename(path))[0]
                
            # 3. Get Artist/Album/Year
            artist = tags.get("artist") or tags.get("ARTIST") or tags.get("©ART") or "Unknown Artist"
            album = tags.get("album") or tags.get("ALBUM") or tags.get("©alb") or ""
            
            year_val = tags.get("date") or tags.get("DATE") or tags.get("original_date") or tags.get("©day") or ""
            year = str(year_val)[:4] if year_val else ""
            
            State.metadata = [artist, title, album, year]
        except:
            State.metadata = ["Metadata Error", os.path.basename(path), "", ""]

    def get_playlist_time(self):
        try:
            if os.path.exists(PLAYLIST_PATH):
                mtime = os.path.getmtime(PLAYLIST_PATH)
                dt = datetime.datetime.fromtimestamp(mtime)
                # This will return "January 8, 2026 • 8:11 PM"
                return dt.strftime("%B %-d, %Y • %-I:%M %p")
            return "Unknown"
        except:
            return "Unknown"

    def do_GET(self):
        clean_path = self.path.split('?')[0]

        if clean_path == '/api/status':
            path = self.get_current_file_path()
            if not path:
                State.current_file = None
                response = {
                    "lines": ["Not Playing"], 
                    "stats": "", 
                    "playlist_time": self.get_playlist_time()
                }
            else:
                self.update_metadata(path)
                self.update_counts(path)
                response = {
                    "lines": State.metadata,
                    "stats": f"Track {State.track_index} of {State.total_count}",
                    "playlist_time": self.get_playlist_time()
                }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
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

        elif clean_path in ['/pause', '/next', '/prev']:
            subprocess.run([f"/usr/local/bin/{clean_path.strip('/')}"])
            self.send_response(200)
            self.end_headers()
            return

        elif clean_path in ['/sick', '/fix']:
            log = REMOVALS_LOG if clean_path == '/sick' else FIXTAGS_LOG
            if State.current_file:
                with open(log, "a") as l: l.write("="*30 + "\n" + State.current_file + "\n\n")
            if clean_path == '/sick': subprocess.run(["/usr/local/bin/next"])
            self.send_response(200)
            self.end_headers()
            return

        super().do_GET()

if __name__ == '__main__':
    os.makedirs(WEB_DIR, exist_ok=True)
    os.chdir(WEB_DIR)
    server = HTTPServer(('0.0.0.0', PORT), MplayerHandler)
    print(f"Music Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()