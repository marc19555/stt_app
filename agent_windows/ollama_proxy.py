"""Proxy local authentifie entre le conteneur Docker et Ollama.

Ollama reste lie a 127.0.0.1:11434. Le proxy n'accepte que les routes utiles,
exige un jeton Bearer et ne journalise jamais les corps de requete.
"""

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from config import (
    OLLAMA_PROXY_BIND,
    OLLAMA_PROXY_PORT,
    OLLAMA_PROXY_TOKEN,
    OLLAMA_UPSTREAM_URL,
)

MAX_BODY_BYTES = 10 * 1024 * 1024
ALLOWED_PATHS = {"/api/generate", "/api/tags", "/api/version"}


class _ProxyHandler(BaseHTTPRequestHandler):
    def _authorized(self):
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {OLLAMA_PROXY_TOKEN}"
        return bool(OLLAMA_PROXY_TOKEN) and hmac.compare_digest(supplied, expected)

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_request(self):
        if not self._authorized():
            self._send_json(401, {"error": "authentification requise"})
            return False
        if self.path not in ALLOWED_PATHS and self.path != "/health":
            self._send_json(404, {"error": "route interdite"})
            return False
        return True

    def do_GET(self):
        if not self._check_request():
            return
        if self.path == "/health":
            try:
                response = requests.get(f"{OLLAMA_UPSTREAM_URL}/api/version", timeout=3)
                response.raise_for_status()
                self._send_json(200, {"status": "ok"})
            except requests.RequestException:
                self._send_json(503, {"status": "ollama_indisponible"})
            return
        self._forward("GET", None)

    def do_POST(self):
        if not self._check_request():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "taille invalide"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "requete trop volumineuse"})
            return
        self._forward("POST", self.rfile.read(length))

    def _forward(self, method, body):
        try:
            response = requests.request(
                method,
                f"{OLLAMA_UPSTREAM_URL}{self.path}",
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=600,
            )
            self.send_response(response.status_code)
            self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)
        except requests.RequestException:
            self._send_json(502, {"error": "Ollama local indisponible"})

    def log_message(self, format, *args):  # noqa: A002
        # Ne pas journaliser l'URL, les en-tetes ou le contenu des reunions.
        return


def start_ollama_proxy():
    if len(OLLAMA_PROXY_TOKEN) < 32:
        raise RuntimeError("OLLAMA_PROXY_TOKEN absent ou trop court; relancez install.ps1")
    server = ThreadingHTTPServer((OLLAMA_PROXY_BIND, OLLAMA_PROXY_PORT), _ProxyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="OllamaProxy")
    thread.start()
    print(f"Proxy Ollama authentifie actif sur le port {OLLAMA_PROXY_PORT}")
    return server
