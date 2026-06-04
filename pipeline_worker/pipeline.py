import os
import sys
import time
import json
import threading
import urllib.request

sys.path.append(os.path.dirname(__file__))
import database as db
from config import DATA_DIR, RAM_LOG_INTERVAL, HOST_RAM_URL


def _fetch_host_ram():
    """Recupere la RAM de la machine hote via l'agent Windows (GET /ram)."""
    try:
        with urllib.request.urlopen(HOST_RAM_URL, timeout=2) as resp:
            data = json.loads(resp.read())
        return data['used_gb'], data['total_gb'], data['percent']
    except Exception:
        return None, None, None


def _print_global_ram_usage(step_name, moment):
    """Affiche la RAM de la machine hote pour faciliter le debug memoire."""
    used_gb, total_gb, percent = _fetch_host_ram()
    if used_gb is None:
        print(f"RAM hote [{step_name}] {moment}: indisponible (agent non joignable)")
        return
    print(
        f"RAM hote [{step_name}] {moment}: {used_gb:.2f}GB/{total_gb:.2f}GB "
        f"({percent:.1f}%)"
    )


def _run_with_ram_monitor(step_name, step_callable):
    """Execute une etape et affiche la RAM pendant l'execution (monitoring live)."""
    stop_event = threading.Event()
    peak_percent = {'value': 0.0}

    def _monitor_loop():
        # Cette boucle tourne en parallele de l'etape pour remonter les pics memoire.
        while not stop_event.wait(RAM_LOG_INTERVAL):
            used_gb, total_gb, percent = _fetch_host_ram()
            if percent is not None:
                peak_percent['value'] = max(peak_percent['value'], percent)
                print(
                    f"RAM hote [{step_name}] live: {used_gb:.2f}GB/{total_gb:.2f}GB "
                    f"({percent:.1f}%)"
                )

    monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    monitor_thread.start()

    step_start = time.perf_counter()
    try:
        result = step_callable()
    finally:
        # On arrete toujours le monitor, meme si l'etape plante.
        stop_event.set()
        monitor_thread.join(timeout=RAM_LOG_INTERVAL + 1)

    step_duration = time.perf_counter() - step_start
    _, _, current_percent = _fetch_host_ram()
    if current_percent is not None:
        peak_percent['value'] = max(peak_percent['value'], current_percent)
    if peak_percent['value'] > 0:
        print(f"RAM hote [{step_name}] pic etape: {peak_percent['value']:.1f}%")

    return result, step_duration


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
    _print_global_ram_usage("pipeline", "debut")
    step_times = {}
    total_start = time.perf_counter()

    # Étape 1 — Prépare l'audio
    print("Préparation audio...")
    _print_global_ram_usage("prepare_audio", "avant")
    from audio_preprocess import prepare_audio
    audio_path, step_times['prepare_audio'] = _run_with_ram_monitor(
        "prepare_audio",
        lambda: prepare_audio(session_id, folder)
    )
    _print_global_ram_usage("prepare_audio", "apres")
    print(f"Préparation audio terminée en {step_times['prepare_audio']:.2f}s")

    # Étape 2 — Diarisation
    print("Diarisation...")
    _print_global_ram_usage("diarization", "avant")
    from diarization import run_diarization
    diarization_path, step_times['diarization'] = _run_with_ram_monitor(
        "diarization",
        lambda: run_diarization(audio_path, folder)
    )
    _print_global_ram_usage("diarization", "apres")
    print(f"Diarisation terminée en {step_times['diarization']:.2f}s")

    # Étape 3 — Transcription
    print("Transcription...")
    _print_global_ram_usage("transcription", "avant")
    from transcription import run_transcription
    transcription_path, step_times['transcription'] = _run_with_ram_monitor(
        "transcription",
        lambda: run_transcription(audio_path, folder)
    )
    _print_global_ram_usage("transcription", "apres")
    print(f"Transcription terminée en {step_times['transcription']:.2f}s")

    # Étape 4 — Fusion speakers + texte
    print("Fusion speakers...")
    _print_global_ram_usage("merge_speakers", "avant")
    from speaker_merger import merge_speakers
    merged_path, step_times['merge_speakers'] = _run_with_ram_monitor(
        "merge_speakers",
        lambda: merge_speakers(diarization_path, transcription_path, folder)
    )
    _print_global_ram_usage("merge_speakers", "apres")
    print(f"Fusion speakers terminée en {step_times['merge_speakers']:.2f}s")

    # Étape 5 — Génération PV
    print("Génération PV...")
    _print_global_ram_usage("generate_pv", "avant")
    from pv_generator import generate_pv
    pv_path, step_times['generate_pv'] = _run_with_ram_monitor(
        "generate_pv",
        lambda: generate_pv(merged_path, folder)
    )
    _print_global_ram_usage("generate_pv", "apres")
    print(f"Génération PV terminée en {step_times['generate_pv']:.2f}s")
    db.save_artifact(session_id, 'pv', pv_path)

    # Étape 6 — Résumé
    print("Génération résumé...")
    _print_global_ram_usage("generate_summary", "avant")
    from summary_generator import generate_summary
    summary_path, step_times['generate_summary'] = _run_with_ram_monitor(
        "generate_summary",
        lambda: generate_summary(merged_path, pv_path, folder)
    )
    _print_global_ram_usage("generate_summary", "apres")
    print(f"Génération résumé terminée en {step_times['generate_summary']:.2f}s")
    db.save_artifact(session_id, 'summary', summary_path)

    # Étape 7 — Export
    print("Export fichiers...")
    _print_global_ram_usage("export", "avant")
    from exporter import export_all
    _, step_times['export'] = _run_with_ram_monitor(
        "export",
        lambda: export_all(session_id, folder, merged_path, pv_path, summary_path)
    )
    _print_global_ram_usage("export", "apres")
    print(f"Export terminé en {step_times['export']:.2f}s")

    total_time = time.perf_counter() - total_start
    print("\n--- Temps pipeline ---")
    for name, duration in step_times.items():
        print(f"{name}: {duration:.2f}s")
    print(f"TOTAL: {total_time:.2f}s")
    _print_global_ram_usage("pipeline", "fin")

    print(f"Pipeline terminé — session {session_id}")