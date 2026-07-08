from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime

DATA_FILE = "/tmp/audits.json"
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audits.json")

def load_audits():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    if os.path.exists(SEED_FILE):
        try:
            with open(SEED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    return []

def save_audits(audits):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(audits, f, indent=4)
    except Exception as e:
        print(f"Error saving audits: {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        content_length_header = self.headers.get('Content-Length')
        content_length = int(content_length_header) if content_length_header else 0
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            payload = json.loads(post_data)
        except Exception:
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode('utf-8'))
            return

        audit_id = payload.get("id")
        vote_type = payload.get("vote")

        if not audit_id or vote_type not in ["vibe", "hand"]:
            self.wfile.write(json.dumps({"error": "ID and valid vote required"}).encode('utf-8'))
            return

        audits = load_audits()
        audit_found = False
        report = {}
        for audit in audits:
            if audit["id"] == str(audit_id):
                if vote_type == "vibe":
                    audit["votes_vibe"] = audit.get("votes_vibe", 0) + 1
                else:
                    audit["votes_hand"] = audit.get("votes_hand", 0) + 1
                audit_found = True
                report = audit
                break
        
        if audit_found:
            save_audits(audits)
            self.wfile.write(json.dumps(report).encode('utf-8'))
        else:
            self.wfile.write(json.dumps({"error": "Audit not found"}).encode('utf-8'))
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        return
