from http.server import BaseHTTPRequestHandler
import json
import os

DATA_FILE = "/tmp/audits.json"
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audits.json")

def reset_audits():
    # Remove ephemeral vercel storage file
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except Exception:
            pass
            
    # Return baseline seed
    if os.path.exists(SEED_FILE):
        try:
            with open(SEED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        baseline = reset_audits()
        self.wfile.write(json.dumps(baseline).encode('utf-8'))
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        return
