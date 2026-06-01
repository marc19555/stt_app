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

    # Lance la diarisation
    diarization = pipeline(audio_path)

    # Convertit en JSON
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 3),
            "end": round(turn.end, 3)
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"Diarisation : {len(segments)} segments → {output_path}")
    return output_path