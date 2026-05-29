import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
import database as db

SESSIONS_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions')

class SessionManager:
    def __init__(self):
        self.current_session_id = None

    def start_session(self, title=None):
        if self.current_session_id is not None:
            print("Une session est déjà en cours")
            return None

        if not title:
            title = f"Réunion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        folder = os.path.join(SESSIONS_ROOT, title)
        os.makedirs(folder, exist_ok=True)

        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO sessions (title, started_at, status, folder_path)
            VALUES (?, datetime('now'), 'recording', ?)
        """, (title, folder))
        conn.commit()
        self.current_session_id = c.lastrowid
        conn.close()

        print(f"Session démarrée : {title} (id={self.current_session_id})")
        return self.current_session_id

    def stop_session(self):
        if self.current_session_id is None:
            print("Aucune session en cours")
            return

        # Merge les chunks
        from audio_chunker import merge_chunks
        conn = db.get_connection()
        row = conn.execute("SELECT folder_path FROM sessions WHERE id = ?",
                           (self.current_session_id,)).fetchone()
        conn.close()
        merge_chunks(self.current_session_id, row['folder_path'])

        # Met à jour le statut + crée le job
        conn = db.get_connection()
        conn.execute("""
            UPDATE sessions
            SET stopped_at = datetime('now'), status = 'recording_done'
            WHERE id = ?
        """, (self.current_session_id,))
        conn.execute("""
            INSERT INTO jobs (session_id, job_type, status, priority)
            VALUES (?, 'full_pipeline', 'pending', 1)
        """, (self.current_session_id,))
        conn.commit()
        conn.close()

        print(f"Session arrêtée (id={self.current_session_id}) → job créé")
        self.current_session_id = None


# Test
if __name__ == "__main__":
    sm = SessionManager()
    sm.start_session()
    input("Appuie sur Entrée pour arrêter la session...")
    sm.stop_session()
    print("Vérifie dans DB Browser : tables sessions + jobs")
