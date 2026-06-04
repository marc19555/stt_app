import os
import sys
import json

sys.path.append(os.path.dirname(__file__))
from config import PYANNOTE_MODEL, HF_TOKEN

def run_diarization(audio_path, session_folder):
    """
    Lance la diarisation avec pyannote.
    Retourne le chemin du fichier diarization.json
    """
    output_folder = os.path.join(session_folder, 'diarization')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, 'diarization.json')

    # Charge le modèle
    from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained(
        PYANNOTE_MODEL,
        token=HF_TOKEN
    )

    # Lance la diarisation (renvoie un objet DiarizeOutput)
    diarization = pipeline(audio_path)

    # Convertit en JSON
    raw_segments = []

    # CORRECTION : On cible l'attribut qui contient la vraie annotation de la v4
    annotation = diarization.speaker_diarization

    # On peut maintenant itérer proprement comme avant
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        raw_segments.append({
            "speaker": speaker,
            "start": round(turn.start, 3),
            "end": round(turn.end, 3)
        })

    # Numerotation des speakers par ordre de premiere apparition.
    speaker_map = {}
    for seg in raw_segments:
        raw = seg["speaker"]
        if raw not in speaker_map:
            speaker_map[raw] = f"Intervenant_{len(speaker_map) + 1}"

    segments = [
        {**seg, "speaker": speaker_map[seg["speaker"]]}
        for seg in raw_segments
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    # Sauvegarde le mapping brut -> numerote pour reference.
    mapping_path = os.path.join(output_folder, 'speaker_map.json')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(speaker_map, f, ensure_ascii=False, indent=2)

    speakers_str = ", ".join(f"{k}->{v}" for k, v in speaker_map.items())
    print(f"Diarisation : {len(segments)} segments, {len(speaker_map)} speaker(s) [{speakers_str}] -> {output_path}")
    return output_path