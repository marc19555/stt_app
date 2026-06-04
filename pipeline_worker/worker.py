import time
import sys
import os
import json
import urllib.request

sys.path.append(os.path.dirname(__file__))
from simple_logger import setup_daily_console_log
from config import POLL_INTERVAL, HOST_RAM_URL
import database as db


def _print_idle_ram_reference(context):
    """Affiche une reference RAM hote hors pipeline pour comparer avec les pics de traitement."""
    try:
        with urllib.request.urlopen(HOST_RAM_URL, timeout=2) as resp:
            data = json.loads(resp.read())
        used_gb, total_gb, percent = data['used_gb'], data['total_gb'], data['percent']
        print(
            f"RAM hote reference hors pipeline [{context}]: "
            f"{used_gb:.2f}GB/{total_gb:.2f}GB ({percent:.1f}%)"
        )
    except Exception:
        print(f"RAM hote reference hors pipeline [{context}]: indisponible (agent non joignable)")


class Worker:
    def __init__(self):
        self.running = True
        # Reference initiale: etat memoire avant tout job de pipeline.
        _print_idle_ram_reference("demarrage worker")
        print("Worker démarré — en attente de jobs...")

    def run(self):
        while self.running:
            job = db.get_next_pending_job()

            if job is None:
                print(f"Aucun job en attente, retry dans {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)
                continue

            # Reference juste avant de lancer un pipeline pour cette session.
            _print_idle_ram_reference(f"avant job {job['id']}")
            print(f"Job trouvé : id={job['id']} session={job['session_id']}")
            self._process_job(job)

    def _process_job(self, job):
        job_id = job['id']
        session_id = job['session_id']

        # Marque le job comme en cours
        db.set_job_status(job_id, 'running')
        db.set_session_status(session_id, 'processing')

        try:
            session = db.get_session(session_id)
            if session is None:
                raise Exception(f"Session {session_id} introuvable")

            print(f"Traitement session : {session['title']}")

            # Lance le pipeline complet
            from pipeline import run_pipeline
            run_pipeline(session_id, dict(session))

            db.set_job_status(job_id, 'done')
            db.set_session_status(session_id, 'done')

            print(
                f"Session traitee: #{session_id} | {session['title']} "
                f"| demarre={session['started_at']} | arrete={session['stopped_at']}"
            )
            archived, info = db.archive_successful_session(session_id)
            if archived:
                print(f"Archivage session {session_id}: {info}")
            else:
                print(f"Archivage session {session_id} ignoree: {info}")

            print(f"Job {job_id} terminé avec succès")

        except Exception as e:
            print(f"Job {job_id} échoué : {e}")
            db.set_job_status(job_id, 'failed', error=str(e))
            db.set_session_status(session_id, 'failed')


if __name__ == "__main__":
    # Active la duplication console -> fichier log journalier avant tout print.
    setup_daily_console_log("pipeline_worker")

    worker = Worker()
    worker.run()