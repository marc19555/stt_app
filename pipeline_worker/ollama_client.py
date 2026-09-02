import requests

from config import OLLAMA_FALLBACK_MODEL, OLLAMA_MODEL, OLLAMA_PROXY_TOKEN, OLLAMA_URL


def _headers():
    if not OLLAMA_PROXY_TOKEN:
        raise RuntimeError("OLLAMA_PROXY_TOKEN manquant")
    return {"Authorization": f"Bearer {OLLAMA_PROXY_TOKEN}"}


def generate_text(prompt, temperature, num_predict, num_ctx, timeout):
    """Genere du texte sans jamais journaliser le prompt ou la reponse."""
    models = [OLLAMA_MODEL]
    if OLLAMA_FALLBACK_MODEL and OLLAMA_FALLBACK_MODEL != OLLAMA_MODEL:
        models.append(OLLAMA_FALLBACK_MODEL)

    last_error = None
    for model in models:
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                headers=_headers(),
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "keep_alive": "2m",
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                        "num_ctx": num_ctx,
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_error = exc
            # Le modele de secours sert aux erreurs de chargement/memoire, pas a
            # contourner une erreur d'authentification.
            if getattr(getattr(exc, "response", None), "status_code", None) in (401, 403):
                break
    raise RuntimeError("Generation Ollama impossible; verifiez le proxy et les modeles") from last_error


def unload_model(timeout=30):
    """Demande a Ollama de decharger les modeles de la RAM."""
    results = []
    for model in {OLLAMA_MODEL, OLLAMA_FALLBACK_MODEL}:
        if not model:
            continue
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            headers=_headers(),
            json={"model": model, "keep_alive": 0, "stream": False},
            timeout=timeout,
        )
        if response.status_code == 404:
            continue
        response.raise_for_status()
        results.append(response.json().get("done_reason", "unknown"))
    return ", ".join(results) or "aucun modele charge"
