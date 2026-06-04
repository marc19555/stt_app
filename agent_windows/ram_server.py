"""Serveur HTTP minimal exposant la RAM de la machine hote Windows.

Le pipeline worker (Docker) appelle GET http://host.docker.internal:PORT/ram
et recoit un JSON { used_gb, total_gb, percent }.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import psutil

sys.path.append(os.path.dirname(__file__))
from config import HOST_RAM_SERVER_PORT


class _RamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/ram':
            self.send_response(404)
            self.end_headers()
            return

        vm = psutil.virtual_memory()
        payload = json.dumps({
            'used_gb': vm.used / (1024 ** 3),
            'total_gb': vm.total / (1024 ** 3),
            'percent': vm.percent,
        }).encode()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002
        # Silence les logs HTTP par defaut pour ne pas polluer la console.
        pass


def start_ram_server() -> HTTPServer:
    """Demarre le serveur RAM dans un thread daemon et retourne le serveur."""
    server = HTTPServer(('0.0.0.0', HOST_RAM_SERVER_PORT), _RamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Serveur RAM hote demarre sur le port {HOST_RAM_SERVER_PORT}")
    return server
