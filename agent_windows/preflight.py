import argparse
import os
import socket
import sqlite3
import sys

import requests

from config import DB_PATH, OLLAMA_PROXY_PORT, OLLAMA_UPSTREAM_URL


def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def checks(include_microphone=True):
    results = []
    try:
        response = requests.get(f"{OLLAMA_UPSTREAM_URL}/api/version", timeout=3)
        results.append((response.status_code == 200, "Ollama local"))
    except requests.RequestException:
        results.append((False, "Ollama local"))

    results.append((check_port_available(OLLAMA_PROXY_PORT), f"port proxy {OLLAMA_PROXY_PORT}"))
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        connection = sqlite3.connect(DB_PATH)
        connection.execute("SELECT 1")
        connection.close()
        results.append((True, "SQLite"))
    except (OSError, sqlite3.Error):
        results.append((False, "SQLite"))

    if include_microphone:
        try:
            from recorder import has_audio_input_device
            results.append((has_audio_input_device(), "microphone"))
        except Exception:
            results.append((False, "microphone"))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-microphone", action="store_true")
    args = parser.parse_args()
    results = checks(include_microphone=not args.no_microphone)
    for ok, name in results:
        print(f"[{'OK' if ok else 'ERREUR'}] {name}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
