import os
import sys
import json
sys.path.append(os.path.dirname(__file__))
from config import PV_PREDICT, PV_TEMPERATURE, GLOBAL_CTX, PV_TIMEOUT
from ollama_client import generate_text

SEGMENTS_PER_CHUNK = 50
MAX_CHUNK_CHARS = 20000

def _ask_ollama(prompt):
    return generate_text(
        prompt,
        temperature=PV_TEMPERATURE,
        num_predict=PV_PREDICT,
        num_ctx=GLOBAL_CTX,
        timeout=PV_TIMEOUT,
    )

def _format_transcript(segments):
    """Formate les segments en texte lisible pour Ollama"""
    lines = []
    for s in segments:
        lines.append(f"[{s['speaker']}] ({s['start']:.0f}s) {s['text']}")
    return "\n".join(lines)

def _generate_chunk_pv(segments, chunk_index, total_chunks):
    """Génère un PV partiel pour un chunk de transcript"""
    transcript_text = _format_transcript(segments)
    prompt = f"""Tu rediges des notes administratives fideles a partir d'une transcription.

REGLES IMPERATIVES :
- Ne devine jamais l'identite, la fonction ou le service d'un intervenant.
- Conserve exactement les libelles Intervenant_1, Intervenant_2, etc.
- Distingue faits, propositions, desaccords, decisions, echeances et actions.
- N'invente aucune information et conserve les chiffres, dates et reserves.
- Chaque changement de locuteur commence sur une nouvelle ligne.
- Le document est un brouillon a faire valider par une personne.

Partie {chunk_index}/{total_chunks} :
{transcript_text}

Produis des notes detaillees en francais, avec le titre "BROUILLON - A VALIDER".
"""

    return _ask_ollama(prompt)

def _merge_chunk_pvs(chunk_pvs):
    """Fusion hierarchique afin de ne jamais depasser le contexte 8K."""
    if not chunk_pvs:
        raise ValueError("Aucune note partielle a fusionner")
    if len(chunk_pvs) == 1:
        return chunk_pvs[0]

    groups = []
    current = []
    current_size = 0
    for pv in chunk_pvs:
        if current and current_size + len(pv) > MAX_CHUNK_CHARS:
            groups.append(current)
            current = []
            current_size = 0
        current.append(pv)
        current_size += len(pv)
    if current:
        groups.append(current)

    if len(groups) == len(chunk_pvs):
        groups = [chunk_pvs[i:i + 2] for i in range(0, len(chunk_pvs), 2)]

    if len(groups) > 1:
        return _merge_chunk_pvs([_merge_chunk_pvs(group) for group in groups])

    combined = "\n\n---\n\n".join(
        [f"Partie {i+1}:\n{pv}" for i, pv in enumerate(chunk_pvs)]
    )
    prompt = f"""Tu fusionnes plusieurs parties de notes de reunion.

Voici plusieurs parties d'un procès-verbal d'une même réunion :

{combined}

Fusionne-les sans inventer d'identite ni d'information. Conserve les libelles
Intervenant_N, les desaccords et les incertitudes. Commence par
"# BROUILLON - A VALIDER". Reponds en francais."""

    return _ask_ollama(prompt)


def _chunk_segments(segments):
    chunks = []
    current = []
    current_size = 0
    for segment in segments:
        estimated = len(segment.get('text', '')) + 64
        if current and (
            len(current) >= SEGMENTS_PER_CHUNK
            or current_size + estimated > MAX_CHUNK_CHARS
        ):
            chunks.append(current)
            current = []
            current_size = 0
        current.append(segment)
        current_size += estimated
    if current:
        chunks.append(current)
    return chunks

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
    chunks = _chunk_segments(segments)
    total_chunks = len(chunks)
    if total_chunks == 0:
        raise ValueError("La transcription ne contient aucun segment exploitable")
    print(f"{len(segments)} segments -> {total_chunks} chunk(s)")

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

    print(f"PV généré -> {output_path}")
    return output_path
