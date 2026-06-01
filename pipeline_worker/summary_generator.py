import os
import sys
import json
import requests

sys.path.append(os.path.dirname(__file__))
from config import OLLAMA_URL, OLLAMA_MODEL

def _ask_ollama(prompt):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()['response'].strip()

def generate_summary(merged_path, pv_path, session_folder):
    """
    Génère un résumé structuré depuis le PV.
    Retourne le chemin du fichier resume.md
    """
    output_folder = os.path.join(session_folder, 'outputs')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, 'resume.md')

    # Lit le PV généré
    with open(pv_path, 'r', encoding='utf-8') as f:
        pv_text = f.read()

    # Lit le transcript pour extraire les actions
    with open(merged_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    nb_speakers = len(set(s['speaker'] for s in segments))
    duration_min = round(segments[-1]['end'] / 60, 1) if segments else 0

    prompt = f"""Tu es un assistant spécialisé dans la synthèse de réunions professionnelles.

Voici le procès-verbal d'une réunion ({nb_speakers} participants, {duration_min} minutes) :

{pv_text}

Génère un résumé structuré avec exactement ces sections :

## Résumé exécutif
(2-3 phrases maximum)

## Points clés abordés
(liste à puces,)

## Décisions prises
(liste numérotée)

## points a venir
(liste à puces)

## Levier d'action
(d'après ce qui a été dit, quels sont les points concrêts sur lesquels agir maintenant pour accélérer ou débloquer les projets ? liste à puces, n'invente rien, uniquement à partir du PV)

Réponds en français, de façon concise et professionnelle."""

    summary_text = _ask_ollama(prompt)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)

    print(f"Résumé généré → {output_path}")
    return output_path