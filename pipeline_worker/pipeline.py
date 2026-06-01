import os
import sys

sys.path.append(os.path.dirname(__file__))
import database as db

def run_pipeline(session_id, session):
    folder = session['folder_path']
    print(f"\n--- Pipeline session {session_id} ---")

    # Étape 1 — Prépare l'audio
    print("Préparation audio...")
    from audio_preprocess import prepare_audio
    audio_path = prepare_audio(session_id, folder)

    # Étape 2 — Diarisation
    print("Diarisation...")
    from diarization import run_diarization
    diarization_path = run_diarization(audio_path, folder)

    # Étape 3 — Transcription
    print("Transcription...")
    from transcription import run_transcription
    transcription_path = run_transcription(audio_path, folder)

    # Étape 4 — Fusion speakers + texte
    print("Fusion speakers...")
    from speaker_merger import merge_speakers
    merged_path = merge_speakers(diarization_path, transcription_path, folder)

    # Étape 5 — Génération PV
    print("Génération PV...")
    from pv_generator import generate_pv
    pv_path = generate_pv(merged_path, folder)
    db.save_artifact(session_id, 'pv', pv_path)

    # Étape 6 — Résumé
    print("Génération résumé...")
    from summary_generator import generate_summary
    summary_path = generate_summary(merged_path, pv_path, folder)
    db.save_artifact(session_id, 'summary', summary_path)

    # Étape 7 — Export
    print("Export fichiers...")
    from exporter import export_all
    export_all(session_id, folder, merged_path, pv_path, summary_path)

    print(f"Pipeline terminé — session {session_id}")