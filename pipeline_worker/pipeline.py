import os
import time

import database as db
from config import DATA_DIR, DIARIZATION_ENABLED
from ollama_client import unload_model


def _resolve_session_folder_for_worker(folder_path):
    if not folder_path:
        raise ValueError("folder_path session vide")

    normalized = str(folder_path).replace('\\', '/')
    sessions_root = os.path.realpath(os.path.join(DATA_DIR, 'sessions'))

    def validated(candidate):
        candidate = os.path.realpath(candidate)
        try:
            inside = os.path.commonpath((sessions_root, candidate)) == sessions_root
        except ValueError:
            inside = False
        if not inside:
            raise ValueError("Chemin de session hors du dossier data/sessions")
        return candidate

    if normalized.startswith('/app/data/'):
        relative = normalized[len('/app/data/'):]
        return validated(os.path.join(DATA_DIR, *relative.split('/')))
    if os.path.isabs(folder_path) and os.path.exists(folder_path):
        try:
            return validated(folder_path)
        except ValueError:
            pass

    relative = normalized.lstrip('/')
    if relative.startswith('data/'):
        relative = relative[len('data/'):]
    if relative.startswith('sessions/'):
        return validated(os.path.join(DATA_DIR, *relative.split('/')))

    marker = '/data/'
    idx = normalized.lower().find(marker)
    if idx != -1:
        tail = normalized[idx + len(marker):]
        if tail.startswith('sessions/'):
            return validated(os.path.join(DATA_DIR, *tail.split('/')))
    return validated(os.path.join(DATA_DIR, 'sessions', os.path.basename(relative)))


def _step(name, callback, timings):
    print(f"{name}...")
    started = time.perf_counter()
    result = callback()
    timings[name] = time.perf_counter() - started
    print(f"{name} termine en {timings[name]:.2f}s")
    return result


def run_pipeline(session_id, session):
    """Execute les modeles sequentiellement pour plafonner l'usage memoire."""
    folder = _resolve_session_folder_for_worker(session['folder_path'])
    print(f"Pipeline session {session_id}")
    timings = {}
    total_start = time.perf_counter()

    try:
        from audio_preprocess import prepare_audio
        audio_path = _step(
            "Preparation audio", lambda: prepare_audio(session_id, folder), timings
        )

        diarization_path = None
        if DIARIZATION_ENABLED:
            from diarization import run_diarization
            diarization_path = _step(
                "Diarisation", lambda: run_diarization(audio_path, folder), timings
            )
        else:
            print("Diarisation desactivee (mode faible memoire)")

        from transcription import run_transcription
        transcription_path = _step(
            "Transcription", lambda: run_transcription(audio_path, folder), timings
        )

        from speaker_merger import merge_speakers
        merged_path = _step(
            "Attribution des locuteurs",
            lambda: merge_speakers(diarization_path, transcription_path, folder),
            timings,
        )

        from pv_generator import generate_pv
        pv_path = _step("Generation du PV", lambda: generate_pv(merged_path, folder), timings)
        db.save_artifact(session_id, 'pv', pv_path)

        from summary_generator import generate_summary
        summary_path = _step(
            "Generation du resume",
            lambda: generate_summary(merged_path, pv_path, folder),
            timings,
        )
        db.save_artifact(session_id, 'summary', summary_path)

        from exporter import export_all
        _step(
            "Export des documents",
            lambda: export_all(session_id, folder, merged_path, pv_path, summary_path),
            timings,
        )

        print("Temps pipeline: " + ", ".join(f"{k}={v:.1f}s" for k, v in timings.items()))
        print(f"Pipeline termine en {time.perf_counter() - total_start:.1f}s")
    finally:
        try:
            print(f"Dechargement Ollama: {unload_model()}")
        except Exception:
            print("Avertissement: le modele Ollama n'a pas pu etre decharge")
