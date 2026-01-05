#!/usr/bin/env python3
import os
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configuration - All Absolute Paths
WEB_DIR = "/var/www/html"
CURRENT_INFO = os.path.join(WEB_DIR, "current.txt")
LAST_SYNC_FILE = os.path.join(WEB_DIR, "lastsync")
REMOVALS_LOG = "/home/administrator/removals.txt"
FIXTAGS_LOG = "/home/administrator/fixtags.txt"
MUSIC_DIR = "/mnt/music"
PORT = 80

class MplayerHandler(SimpleHTTPRequestHandler):
    
    def get_track_count(self):
        """Executes the find command to count music files in the music directory."""
        try:
            cmd = f"find {MUSIC_DIR} -type f \( -iname '*.mp3' -o -iname '*.m4a' ! -name '.*' \) | wc -l"
            count = subprocess.check_output(cmd, shell=True).decode().strip()
            return count
        except Exception:
            return "0"

    def append_to_list(self, log_path):
        """Helper to read current.txt and append it to a log file."""
        try:
            if not os.path.exists(CURRENT_INFO):
                content = "No track info found."
            else:
                with open(CURRENT_INFO, "r") as f:
                    content = f.read().strip()
            
            with open(log_path, "a") as log:
                log.write("=" * 30 + "\n")
                log.write(content + "\n\n")
            return True
        except Exception as e:
            print(f"Error logging to {log_path}: {e}")
            return False

    def do_GET(self):
        # Normalize path to ignore query strings (cache busters)
        clean_path = self.path.split('?')[0]

        # 1. Track Count Endpoint
        if clean_path == '/trackcount':
            count = self.get_track_count()
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(count.encode())
            return

        # 2. Last Sync Endpoint
        elif clean_path == '/lastsync':
            content = "Unknown"
            if os.path.exists(LAST_SYNC_FILE):
                with open(LAST_SYNC_FILE, "r") as f:
                    content = f.read().strip()
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(content.encode())
            return

        # 3. Handle current.txt to prevent 404s when music is off
        elif clean_path == '/current.txt':
            if not os.path.exists(CURRENT_INFO):
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(b"Not Playing")
                return
            # If exists, fall through to super().do_GET()

        # 4. Media Controls
        elif clean_path in ['/pause', '/next', '/prev']:
            subprocess.run([f"/usr/local/bin{clean_path}"])
            self.send_response(200)
            self.end_headers()
            return

        # 5. Library Management
        elif clean_path == '/sick':
            if self.append_to_list(REMOVALS_LOG):
                subprocess.run(["/usr/local/bin/next"])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Logged and Skipped")
            return

        elif clean_path == '/fix':
            if self.append_to_list(FIXTAGS_LOG):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Logged")
            return

        # 6. Standard File Serving (index.html, etc.)
        super().do_GET()

def is_mplayer_running():
    """Check if mplayer is currently active."""
    try:
        subprocess.check_output(["pgrep", "mplayer"])
        return True
    except subprocess.CalledProcessError:
        return False

if __name__ == '__main__':
    # Ensure environment is ready
    if not os.path.exists(WEB_DIR):
        os.makedirs(WEB_DIR, exist_ok=True)
    
    os.chdir(WEB_DIR)

    # Cleanup stale current.txt if music isn't playing
    if not is_mplayer_running() and os.path.exists(CURRENT_INFO):
        try:
            os.remove(CURRENT_INFO)
            print("Cleanup: mplayer not running, removed stale current.txt")
        except Exception as e:
            print(f"Cleanup Error: {e}")
    
    # Ensure logs exist and are writable
    for log in [REMOVALS_LOG, FIXTAGS_LOG]:
        if not os.path.exists(log):
            try:
                open(log, 'a').close()
                os.chmod(log, 0o666)
            except Exception as e:
                print(f"Warning: Could not initialize {log}: {e}")

    # Start Server
    server = HTTPServer(('0.0.0.0', PORT), MplayerHandler)
    print(f"Music Server running at http://0.0.0.0:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()