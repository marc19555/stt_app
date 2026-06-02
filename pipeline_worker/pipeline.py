import os
import sys
import time

sys.path.append(os.path.dirname(__file__))
import database as db
from config import DATA_DIR


def _resolve_session_folder_for_worker(folder_path):
    if not folder_path:
        raise ValueError("folder_path session vide")

    normalized = str(folder_path).replace('\\', '/')

    # Cas déjà correct dans Docker
    if normalized.startswith('/app/data/'):
        return normalized

    # Cas absolu existant (exécution locale hors Docker)
    if os.path.isabs(folder_path) and os.path.exists(folder_path):
        return folder_path

    # Cas relatif recommandé: sessions/<nom>
    relative = normalized.lstrip('/')
    if relative.startswith('data/'):
        relative = relative[len('data/'):]
    if relative.startswith('sessions/'):
        return os.path.join(DATA_DIR, relative)

    # Cas legacy Windows stocké en DB: .../data/sessions/<nom>
    marker = '/data/'
    idx = normalized.lower().find(marker)
    if idx != -1:
        tail = normalized[idx + len(marker):]
        if tail.startswith('sessions/'):
            return os.path.join(DATA_DIR, tail)

    # Fallback: infère le nom de session
    return os.path.join(DATA_DIR, 'sessions', os.path.basename(relative))

def run_pipeline(session_id, session):
    folder = _resolve_session_folder_for_worker(session['folder_path'])
    print(f"\n--- Pipeline session {session_id} ---")
    step_times = {}
    total_start = time.perf_counter()

    # Étape 1 — Prépare l'audio
    print("Préparation audio...")
    from audio_preprocess import prepare_audio
    step_start = time.perf_counter()
    audio_path = prepare_audio(session_id, folder)
    step_times['prepare_audio'] = time.perf_counter() - step_start
    print(f"Préparation audio terminée en {step_times['prepare_audio']:.2f}s")

    # Étape 2 — Diarisation
    print("Diarisation...")
    from diarization import run_diarization
    step_start = time.perf_counter()
    diarization_path = run_diarization(audio_path, folder)
    step_times['diarization'] = time.perf_counter() - step_start
    print(f"Diarisation terminée en {step_times['diarization']:.2f}s")

    # Étape 3 — Transcription
    print("Transcription...")
    from transcription import run_transcription
    step_start = time.perf_counter()
    transcription_path = run_transcription(audio_path, folder)
    step_times['transcription'] = time.perf_counter() - step_start
    print(f"Transcription terminée en {step_times['transcription']:.2f}s")

    # Étape 4 — Fusion speakers + texte
    print("Fusion speakers...")
    from speaker_merger import merge_speakers
    step_start = time.perf_counter()
    merged_path = merge_speakers(diarization_path, transcription_path, folder)
    step_times['merge_speakers'] = time.perf_counter() - step_start
    print(f"Fusion speakers terminée en {step_times['merge_speakers']:.2f}s")

    # Étape 5 — Génération PV
    print("Génération PV...")
    from pv_generator import generate_pv
    step_start = time.perf_counter()
    pv_path = generate_pv(merged_path, folder)
    step_times['generate_pv'] = time.perf_counter() - step_start
    print(f"Génération PV terminée en {step_times['generate_pv']:.2f}s")
    db.save_artifact(session_id, 'pv', pv_path)

    # Étape 6 — Résumé
    print("Génération résumé...")
    from summary_generator import generate_summary
    step_start = time.perf_counter()
    summary_path = generate_summary(merged_path, pv_path, folder)
    step_times['generate_summary'] = time.perf_counter() - step_start
    print(f"Génération résumé terminée en {step_times['generate_summary']:.2f}s")
    db.save_artifact(session_id, 'summary', summary_path)

    # Étape 7 — Export
    print("Export fichiers...")
    from exporter import export_all
    step_start = time.perf_counter()
    export_all(session_id, folder, merged_path, pv_path, summary_path)
    step_times['export'] = time.perf_counter() - step_start
    print(f"Export terminé en {step_times['export']:.2f}s")

    total_time = time.perf_counter() - total_start
    print("\n--- Temps pipeline ---")
    for name, duration in step_times.items():
        print(f"{name}: {duration:.2f}s")
    print(f"TOTAL: {total_time:.2f}s")

    print(f"Pipeline terminé — session {session_id}")