#!/usr/bin/env python3
import json
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

VISITORS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visitors.json")

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/visitors":
            visitors = []
            if os.path.exists(VISITORS_FILE):
                with open(VISITORS_FILE, "r") as f:
                    visitors = json.load(f)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(visitors, ensure_ascii=False).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/visitor":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            name = body.get("name", "").strip()
            if not name:
                self.send_response(400)
                self.end_headers()
                return

            # Load existing visitors
            visitors = []
            if os.path.exists(VISITORS_FILE):
                with open(VISITORS_FILE, "r") as f:
                    visitors = json.load(f)

            # Add new visitor
            visitors.append({
                "name": name,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Save
            with open(VISITORS_FILE, "w") as f:
                json.dump(visitors, f, indent=2, ensure_ascii=False)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        else:
            self.send_response(404)
            self.end_headers()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(os.environ.get("PORT", 3000))
print(f"Serveur LoveSpark sur http://0.0.0.0:{port}")
HTTPServer(("0.0.0.0", port), Handler).serve_forever()
