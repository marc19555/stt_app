import time
import sys
import os

sys.path.append(os.path.dirname(__file__))
from config import POLL_INTERVAL
import database as db

class Worker:
    def __init__(self):
        self.running = True
        print("Worker démarré — en attente de jobs...")

    def run(self):
        while self.running:
            job = db.get_next_pending_job()

            if job is None:
                print(f"Aucun job en attente, retry dans {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)
                continue

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
            print(f"Job {job_id} terminé avec succès")

        except Exception as e:
            print(f"Job {job_id} échoué : {e}")
            db.set_job_status(job_id, 'failed', error=str(e))
            db.set_session_status(session_id, 'failed')


if __name__ == "__main__":
    worker = Worker()
    worker.run()