#!/usr/bin/env python3
import json
import os
import re
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Load .env file (stdlib, no dependency)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

from ai_providers import get_ai_message, VALID_SIGNS

VISITORS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visitors.json")
TRUSTED_PROXY = os.environ.get("TRUSTED_PROXY", "").strip()
ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()
MAX_NAME_LENGTH = 30
NAME_PATTERN = re.compile(r"^[a-zA-ZÀ-ÿ\s\-']+$")
BIRTHDATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BIRTHTIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")

# --- Rate limiting (in-memory) ---
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "50"))  # max AI calls per hour
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
_ai_call_timestamps: list[float] = []
MAX_BODY_SIZE = 1024  # 1 KB max request body


def _check_rate_limit() -> bool:
    """Return True if the AI call is allowed, False if rate limited."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    # Purge old timestamps
    while _ai_call_timestamps and _ai_call_timestamps[0] < cutoff:
        _ai_call_timestamps.pop(0)
    if len(_ai_call_timestamps) >= RATE_LIMIT_MAX:
        return False
    _ai_call_timestamps.append(now)
    return True


def load_visitors():
    if os.path.exists(VISITORS_FILE):
        with open(VISITORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_visitors(visitors):
    with open(VISITORS_FILE, "w", encoding="utf-8") as f:
        json.dump(visitors, f, indent=2, ensure_ascii=False)


def sanitize_name(raw: str) -> str | None:
    """Validate and sanitize the name. Returns None if invalid."""
    name = raw.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        return None
    if not NAME_PATTERN.match(name):
        return None
    return name


class Handler(SimpleHTTPRequestHandler):

    def get_client_ip(self):
        # Only trust X-Forwarded-For if TRUSTED_PROXY is configured
        # and the direct connection comes from the trusted proxy
        if TRUSTED_PROXY and self.client_address[0] == TRUSTED_PROXY:
            forwarded = self.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def send_json(self, data, status=200, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    # ---- GET ----
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/visitors":
            # Protected by ADMIN_KEY
            params = parse_qs(parsed.query)
            key = params.get("key", [""])[0]
            if not ADMIN_KEY or key != ADMIN_KEY:
                self.send_json({"error": "Forbidden"}, 403)
                return
            self.send_json(load_visitors())

        elif parsed.path == "/api/my-message":
            params = parse_qs(parsed.query)
            name = params.get("name", [""])[0].strip()
            if not name:
                self.send_json({"error": "name required"}, 400)
                return
            visitors = load_visitors()
            for v in visitors:
                if v.get("name", "").lower() == name.lower():
                    msg = v.get("message")
                    if msg:
                        self.send_json({"ok": True, "message": msg})
                        return
                    self.send_json({"error": "Message indisponible"}, 503)
                    return
            self.send_json({"error": "Aucun message trouve pour ce prenom"}, 404)

        else:
            super().do_GET()

    # ---- POST ----
    def do_POST(self):
        if self.path == "/api/visitor":
            # Check body size
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY_SIZE:
                self.send_json({"error": "Request too large"}, 413)
                return

            body = json.loads(self.rfile.read(length))
            raw_name = body.get("name", "")

            # Validate name (anti prompt injection + sanity)
            name = sanitize_name(raw_name)
            if not name:
                self.send_json({"error": "Prenom invalide (lettres, espaces, tirets, max 30 caracteres)"}, 400)
                return

            # Validate sign (optional, but if provided must be in allowlist)
            sign_raw = (body.get("sign") or "").strip().lower()
            sign = sign_raw if sign_raw in VALID_SIGNS else None

            # Birthdate: required only if client used "Je ne sais pas" path.
            # Accept YYYY-MM-DD and HH:MM. Stored as-is, not used for generation.
            birthdate_raw = (body.get("birthdate") or "").strip()
            birthtime_raw = (body.get("birthtime") or "").strip()
            birthdate = birthdate_raw if BIRTHDATE_PATTERN.match(birthdate_raw) else ""
            birthtime = birthtime_raw if BIRTHTIME_PATTERN.match(birthtime_raw) else ""

            client_ip = self.get_client_ip()
            visitors = load_visitors()

            # Security: check cookie
            cookie_header = self.headers.get("Cookie", "")
            if "love_visited=1" in cookie_header:
                self.send_json({
                    "already_visited": True,
                    "name": name,
                    "message": "Tu as deja decouvert ton message."
                }, 403)
                return

            # Security: check IP
            for v in visitors:
                if v.get("ip") == client_ip:
                    existing_name = v.get("name", name)
                    stored_msg = v.get("message")
                    if not stored_msg:
                        self.send_json({"error": "Message indisponible"}, 503)
                        return
                    self.send_json({
                        "already_visited": True,
                        "name": existing_name,
                        "message": stored_msg,
                    }, 403)
                    return

            # Rate limiting
            if not _check_rate_limit():
                self.send_json(
                    {"error": "Trop de demandes, reessaye dans un instant"},
                    503,
                    {"Retry-After": "60"},
                )
                return

            message = get_ai_message(name, sign)
            if not message:
                self.send_json(
                    {"error": "Generation du message impossible, reessaye dans un instant"},
                    503,
                )
                return

            # Save visitor
            visitors.append({
                "name": name,
                "sign": sign or "",
                "birthdate": birthdate,
                "birthtime": birthtime,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip": client_ip,
                "message": message,
            })
            save_visitors(visitors)

            # Respond with cookie
            self.send_json(
                {"ok": True, "message": message},
                200,
                {"Set-Cookie": "love_visited=1; HttpOnly; Path=/; Max-Age=31536000; SameSite=Strict"}
            )
        else:
            self.send_response(404)
            self.end_headers()


os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(os.environ.get("PORT", 3000))
print(f"Serveur LoveSpark sur http://0.0.0.0:{port}")
HTTPServer(("0.0.0.0", port), Handler).serve_forever()
