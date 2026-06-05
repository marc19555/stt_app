import os
import sys
import json
import requests

sys.path.append(os.path.dirname(__file__))
from config import OLLAMA_URL, OLLAMA_MODEL, SUMMARY_TEMPERATURE, SUMMARY_PREDICT, GOLBAL_CTX, SUMMARY_TIMEOUT

def _ask_ollama(prompt):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": SUMMARY_TEMPERATURE,
                "num_predict": SUMMARY_PREDICT,
                "num_ctx": GOLBAL_CTX
            }
        },
        timeout=SUMMARY_TIMEOUT
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

    prompt = f"""
"/nothink\n"
"Tu es un rédacteur administratif chargé d'extraire les points clés de notes de réunion "
"produites pour la Direction interrégionale des services pénitentiaires du Grand Est, "
"dans le cadre de l'administration pénitentiaire.\n\n"
"OBJECTIF :\n"
"À partir des notes détaillées d'une réunion, extraire les éléments réellement utiles "
"pour préparer un compte rendu, un procès-verbal, une note de synthèse ou un relevé de décisions.\n\n"

"CONSIGNES :\n"
"- Liste uniquement les points importants : décisions, arbitrages, engagements, demandes, "
"alertes, désaccords, difficultés signalées, réponses apportées, échéances, actions à suivre "
"et questions restées ouvertes.\n"
"- Format obligatoire : liste à puces.\n"
"- Une puce = une idée ou un point d'action clairement identifiable.\n"
"- Identifie toujours qui porte le point : direction, président de séance, service concerné, "
"établissement, organisation syndicale, agent, intervenant, ou à défaut la balise locuteur.\n"
"- Conserve les noms de services, organisations, établissements, lieux, chiffres, dates, délais, "
"effectifs, montants et références réglementaires.\n"
"- Distingue clairement : ce qui est acté, ce qui est seulement proposé, ce qui est contesté, "
"ce qui doit être vérifié et ce qui reste en attente.\n"
"- Ne crée pas de décision si les notes indiquent seulement une discussion ou une hypothèse.\n"
"- Ne généralise pas abusivement : reste fidèle aux notes.\n"
"- Supprime les répétitions entre intervenants, mais conserve les désaccords et positions "
"différentes lorsqu'elles existent.\n"
"- Maximum 15 points clés pour ce groupe, sauf si la réunion contient beaucoup de décisions "
"distinctes ; dans ce cas, conserve tous les points indispensables.\n\n"

Voici le procès-verbal d'une réunion ({nb_speakers} participants, {duration_min} minutes) :

{pv_text}

"FORMAT ATTENDU :\n"

## Résumé thématique
(10 thématiques maximum)

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