import os
import sys
import json
sys.path.append(os.path.dirname(__file__))
from config import SUMMARY_TEMPERATURE, SUMMARY_PREDICT, GLOBAL_CTX, SUMMARY_TIMEOUT
from ollama_client import generate_text

def _ask_ollama(prompt):
    return generate_text(
        prompt,
        temperature=SUMMARY_TEMPERATURE,
        num_predict=SUMMARY_PREDICT,
        num_ctx=GLOBAL_CTX,
        timeout=SUMMARY_TIMEOUT,
    )

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

    prompt = f"""Tu rediges un resume administratif fidele et concis en francais.

La reunion dure environ {duration_min} minutes et comporte {nb_speakers} libelle(s)
d'intervenant.

REGLES IMPERATIVES :
- Ne devine jamais une identite, une fonction ou un service. Conserve exactement
  Intervenant_1, Intervenant_2, etc., sauf si l'information est explicitement dite.
- N'invente aucun fait, aucune decision ni aucune echeance.
- Distingue ce qui est acte, propose, conteste, a verifier ou encore en attente.
- Conserve les chiffres, dates, delais, montants et references explicites.
- Supprime les repetitions sans effacer les desaccords.
- Limite les points cles aux elements reellement utiles.

FORMAT OBLIGATOIRE :
# BROUILLON - A VALIDER
## Resume thematique
## Points cles abordes
## Decisions prises
## Points a venir
## Leviers d'action

Sous chaque rubrique, utilise des puces courtes. Si une rubrique n'est pas
documentee, ecris "Aucun element explicite dans la transcription".

PROCES-VERBAL SOURCE :
{pv_text}
"""

    summary_text = _ask_ollama(prompt)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)

    print(f"Résumé généré -> {output_path}")
    return output_path
