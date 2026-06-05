import os
import sys
import json
import gc

sys.path.append(os.path.dirname(__file__))
from config import WHISPER_MODEL, WHISPER_LANGUAGE

def run_transcription(audio_path, session_folder):
    """
    Transcrit l'audio avec faster-whisper.
    Retourne le chemin du fichier transcript.json
    """
    output_folder = os.path.join(session_folder, 'transcription')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, 'transcript.json')

    # Charge le modèle
    from faster_whisper import WhisperModel
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    # Transcription
    segments, info = model.transcribe(
        audio_path,
        language=WHISPER_LANGUAGE,
        beam_size=5,
        word_timestamps=True
    )

    # Convertit en JSON
    transcript = []
    for segment in segments:
        transcript.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip()
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    print(f"Transcription : {len(transcript)} segments → {output_path}")

    # Libère le modèle Whisper de la RAM
    del model
    gc.collect()

    return output_path