from http.server import BaseHTTPRequestHandler
import json
import os

DATA_FILE = "/tmp/audits.json"
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audits.json")

def load_audits():
    # Load from /tmp if available
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    # Fallback to seed file
    if os.path.exists(SEED_FILE):
        try:
            with open(SEED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    return []

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
        audits = load_audits()
        audits_sorted = sorted(audits, key=lambda x: x.get("date", ""), reverse=True)
        self.wfile.write(json.dumps(audits_sorted).encode('utf-8'))
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        return
