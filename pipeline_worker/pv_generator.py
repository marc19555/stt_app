import os
import sys
import json
import requests

sys.path.append(os.path.dirname(__file__))
from config import OLLAMA_URL, OLLAMA_MODEL, PV_PREDICT,PV_TEMPERATURE,GOLBAL_CTX,PV_TIMEOUT

# Nombre de segments par chunk (pour les longues réunions)
SEGMENTS_PER_CHUNK = 50

def _ask_ollama(prompt):
    """Envoie un prompt à Ollama et retourne la réponse"""
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": PV_TEMPERATURE,
                "num_predict": PV_PREDICT,
                "num_ctx": GOLBAL_CTX
            }
        },
        timeout=PV_TIMEOUT
    )
    response.raise_for_status()
    return response.json()['response'].strip()

def _format_transcript(segments):
    """Formate les segments en texte lisible pour Ollama"""
    lines = []
    for s in segments:
        lines.append(f"[{s['speaker']}] ({s['start']:.0f}s) {s['text']}")
    return "\n".join(lines)

def _generate_chunk_pv(segments, chunk_index, total_chunks):
    """Génère un PV partiel pour un chunk de transcript"""
    transcript_text = _format_transcript(segments)
    prompt = f"""
    "/nothink\n"
    "Tu es un rédacteur administratif chargé de produire des notes détaillées de réunion "
    "pour la Direction interrégionale des services pénitentiaires du Grand Est, dans le cadre "
    "de l'administration pénitentiaire.\n\n"
    "OBJECTIF :\n"
    "À partir d'une transcription STT avec diarisation, produire une restitution détaillée, "
    "fidèle et exploitable pour la rédaction ultérieure d'un compte rendu, d'un procès-verbal "
    "ou d'une synthèse administrative.\n"
    "La réunion peut être de toute nature : CODIR, réunion de direction, réunion RH, réunion "
    "technique, réunion syndicale, CSA, formation spécialisée, réunion SST, réunion établissement, "
    "SPIP, PREJ, ERIS, sécurité, détention, insertion-probation, organisation de service, "
    "gestion des effectifs, dialogue social ou tout autre sujet relevant de la DISP Grand Est.\n\n"

    "CONSIGNES STRICTES :\n"
    "1. Utilise le discours rapporté au présent : par exemple « Le directeur indique que », "
    "« La représentante syndicale répond que », « Le service RH précise que ».\n"
    "2. Chaque intervention DOIT commencer sur une NOUVELLE LIGNE par le nom de l'orateur, "
    "du service, de la fonction, de l'organisation ou, à défaut, par la balise locuteur "
    "du type [SPEAKER_00].\n"
    "3. Un changement d'orateur = un retour à la ligne. Ne fusionne jamais deux interventions "
    "différentes sur la même ligne.\n"
    "4. Identifie les locuteurs grâce aux balises de diarisation, au contexte, aux fonctions "
    "mentionnées et aux éléments de langage. Si l'identité n'est pas certaine, conserve la balise "
    "et ajoute une hypothèse prudente entre parenthèses, par exemple : [SPEAKER_02 - probablement RH].\n"
    "5. Ne supprime aucun argument de fond, même mineur. Les banalités, hésitations et répétitions "
    "peuvent être légèrement synthétisées, mais les positions, demandes, alertes, objections, "
    "réponses, engagements, arbitrages et désaccords doivent être conservés.\n"
    "6. Conserve précisément les chiffres

    Voici une partie ({chunk_index}/{total_chunks}) de la transcription d'une réunion :

    {transcript_text}

    """

    return _ask_ollama(prompt)

def _merge_chunk_pvs(chunk_pvs):
    """Fusionne les PVs partiels en un PV final cohérent"""
    combined = "\n\n---\n\n".join(
        [f"Partie {i+1}:\n{pv}" for i, pv in enumerate(chunk_pvs)]
    )
    prompt = f"""Tu es un assistant spécialisé dans le nettoyage de texte.

Voici plusieurs parties d'un procès-verbal d'une même réunion :

{combined}

Fusionne ces parties en un seul procès-verbal cohérent et de qualité professionnelle. Supprime les redondances et assure-toi que le résultat final soit fluide et structuré.
Réponds en français."""

    return _ask_ollama(prompt)

def generate_pv(merged_path, session_folder):
    """
    Génère le procès-verbal depuis le transcript fusionné.
    Gère les longues réunions par chunks.
    Retourne le chemin du fichier pv.md
    """
    output_folder = os.path.join(session_folder, 'outputs')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, 'pv.md')

    with open(merged_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    # Découpe en chunks si nécessaire
    chunks = [
        segments[i:i + SEGMENTS_PER_CHUNK]
        for i in range(0, len(segments), SEGMENTS_PER_CHUNK)
    ]
    total_chunks = len(chunks)
    print(f"{len(segments)} segments → {total_chunks} chunk(s)")

    if total_chunks == 1:
        # Réunion courte → génération directe
        pv_text = _generate_chunk_pv(chunks[0], 1, 1)
    else:
        # Réunion longue → génération par chunks puis fusion
        chunk_pvs = []
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1}/{total_chunks}...")
            chunk_pv = _generate_chunk_pv(chunk, i+1, total_chunks)
            chunk_pvs.append(chunk_pv)
        print("Fusion des chunks...")
        pv_text = _merge_chunk_pvs(chunk_pvs)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pv_text)

    print(f"PV généré → {output_path}")
    return output_path