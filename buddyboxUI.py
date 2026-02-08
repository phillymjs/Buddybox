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

class BuddyBoxHandler(SimpleHTTPRequestHandler):

    def get_mpv_status(self):
        """Queries MPV via socket for path, pause state, and playlist position."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.connect(MPV_SOCKET)

                # Get current file path
                s.sendall(json.dumps({"command": ["get_property", "path"]}).encode() + b"\n")
                path_data = json.loads(s.recv(4096).decode().splitlines()[0])

                # Get pause state
                s.sendall(json.dumps({"command": ["get_property", "pause"]}).encode() + b"\n")
                pause_data = json.loads(s.recv(4096).decode().splitlines()[0])

                # Get current track index (0-based)
                s.sendall(json.dumps({"command": ["get_property", "playlist-pos"]}).encode() + b"\n")
                pos_data = json.loads(s.recv(4096).decode().splitlines()[0])

                # MPV returns 0 for the first track; we add 1 for human-readable display
                raw_index = pos_data.get("data")
                track_num = str(raw_index + 1) if raw_index is not None else "0"

                return path_data.get("data"), pause_data.get("data", False), track_num
        except Exception:
            return None, False, "0"

    def update_counts(self, track_num):
        """Updates total count once and sets current track index from MPV data."""
        try:
            if State.total_count == "0":
                find_cmd = ["find", MUSIC_DIR, "-type", "f", "(", "-iname", "*.mp3", "-o", "-iname", "*.m4a", ")", "!", "-path", "*/.*", "!", "-name", "._*"]
                find_out = subprocess.check_output(find_cmd)
                State.total_count = str(len(find_out.decode().splitlines()))

            State.track_index = track_num
        except Exception:
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
        except Exception:
            State.metadata = ["Metadata Error", os.path.basename(path), "", ""]

    def get_playlist_time(self):
        try:
            if os.path.exists(PLAYLIST_PATH):
                mtime = os.path.getmtime(PLAYLIST_PATH)
                dt = datetime.datetime.fromtimestamp(mtime)
                return dt.strftime("%B %-d, %Y • %-I:%M %p")
            return "Unknown"
        except Exception:
            return "Unknown"

    def get_lastsync_time(self):
        try:
            if os.path.exists(LAST_SYNC_FILE):
                mtime = os.path.getmtime(LAST_SYNC_FILE)
                dt = datetime.datetime.fromtimestamp(mtime)
                return dt.strftime("%B %-d, %Y • %-I:%M %p")
            return "Unknown"
        except Exception:
            return "Unknown"

    def do_GET(self):
        clean_path = self.path.split('?')[0]
        user_agent = self.headers.get('User-Agent', '').lower()
        is_cli = 'curl' in user_agent or 'wget' in user_agent

        def handle_response():
            if is_cli:
                self.send_response(200)
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()

        if clean_path == '/api/status':
            path, is_paused, track_num = self.get_mpv_status()
            State.is_paused = is_paused
            is_locked = os.path.exists(os.path.join(MUSIC_DIR, ".lockout"))

            if not path:
                State.current_file = None
                response = {
                    "lines": ["Not Playing", "", "", ""],
                    "stats": "",
                    "playlist_time": self.get_playlist_time(),
                    "lastsync_time": self.get_lastsync_time(),
                    "paused": True,
                    "locked": is_locked
                }
            else:
                self.update_metadata(path)
                self.update_counts(track_num)
                response = {
                    "lines": State.metadata,
                    "stats": f"Track {State.track_index} of {State.total_count}",
                    "playlist_time": self.get_playlist_time(),
                    "lastsync_time": self.get_lastsync_time(),
                    "paused": State.is_paused,
                    "locked": is_locked
                }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        elif clean_path == '/lock':
            subprocess.Popen(["/usr/local/bin/bb-lock", "1"])
            handle_response()
            return

        elif clean_path == '/unlock':
            subprocess.Popen(["/usr/local/bin/bb-lock", "0"])
            handle_response()
            return

        elif clean_path in ['/next', '/prev', '/pause']:
            subprocess.Popen([f"/usr/local/bin/bb-{clean_path.strip('/')}"])
            handle_response()
            return

        elif clean_path in ['/fade-out', '/fade-in']:
            direction = "out" if "fade-out" in clean_path else "in"
            query = self.path.split('?')
            duration = query[1] if len(query) > 1 and query[1].isdigit() else None
            cmd = ["/usr/local/bin/bb-fade", direction]
            if duration: cmd.append(duration)
            subprocess.Popen(cmd)
            handle_response()
            return

        elif clean_path in ['/sick', '/fix']:
            log = REMOVALS_LOG if clean_path == '/sick' else FIXTAGS_LOG
            if State.current_file and len(State.metadata) >= 3:
                log_entry = f"{State.metadata[0]} - {State.metadata[1]} - {State.metadata[2]}\n"
                with open(log, "a") as l: l.write(log_entry)

            if clean_path == '/sick':
                subprocess.run(["/usr/local/bin/bb-next"])

            handle_response()
            return

        return super().do_GET()

if __name__ == '__main__':
    os.makedirs(WEB_DIR, exist_ok=True)
    os.chdir(WEB_DIR)
    server = HTTPServer(('0.0.0.0', PORT), BuddyBoxHandler)
    print(f"BuddyBox UI Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
