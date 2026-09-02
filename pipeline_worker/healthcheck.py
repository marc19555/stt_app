import os
import sqlite3
import sys

import requests

from config import DB_PATH, OLLAMA_PROXY_TOKEN, OLLAMA_URL


def main():
    if not OLLAMA_PROXY_TOKEN:
        return 1
    try:
        connection = sqlite3.connect(DB_PATH, timeout=3)
        connection.execute("SELECT 1")
        connection.close()
        response = requests.get(
            f"{OLLAMA_URL}/health",
            headers={"Authorization": f"Bearer {OLLAMA_PROXY_TOKEN}"},
            timeout=3,
        )
        return 0 if response.status_code == 200 else 1
    except (OSError, sqlite3.Error, requests.RequestException):
        return 1


if __name__ == "__main__":
    sys.exit(main())
