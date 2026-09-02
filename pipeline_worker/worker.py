import time
import sys
import os

sys.path.append(os.path.dirname(__file__))
from simple_logger import setup_daily_console_log
from config import DOCUMENT_RETENTION_DAYS, POLL_INTERVAL
import database as db


class Worker:
    def __init__(self):
        self.running = True
        db.init_db()
        recovered, failed = db.recover_stuck_jobs()
        if recovered or failed:
            print(f"Reprise jobs: {recovered} remis en attente, {failed} en echec")
        purged = db.purge_expired_sessions(DOCUMENT_RETENTION_DAYS)
        if purged:
            print(f"Retention: {purged} session(s) purgee(s)")
        self._last_purge = time.monotonic()
        print("Worker démarré — en attente de jobs...")

    def run(self):
        while self.running:
            job = db.claim_next_pending_job()

            if job is None:
                if time.monotonic() - self._last_purge >= 3600:
                    purged = db.purge_expired_sessions(DOCUMENT_RETENTION_DAYS)
                    if purged:
                        print(f"Retention: {purged} session(s) purgee(s)")
                    self._last_purge = time.monotonic()
                print(f"Aucun job en attente, retry dans {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)
                continue

            print(f"Job trouvé : id={job['id']} session={job['session_id']}")
            self._process_job(job)

    def _process_job(self, job):
        job_id = job['id']
        session_id = job['session_id']

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
