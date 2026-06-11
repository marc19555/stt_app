import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))
from config import OLLAMA_MODEL, OLLAMA_URL


def unload_model(timeout=30):
    """Demande a Ollama de decharger le modele de la RAM."""
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "keep_alive": 0,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get('done_reason', 'unknown')