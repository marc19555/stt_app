import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
import database as db

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
SESSIONS_ROOT = os.path.join(DATA_ROOT, 'sessions')


def _resolve_session_folder(folder_path):
    """Resolve legacy or relative DB folder paths to an absolute local path."""
    if not folder_path:
        return None

    normalized = str(folder_path).replace('\\', '/')

    if os.path.isabs(folder_path) and os.path.exists(folder_path):
        return folder_path

    if normalized.startswith('data/'):
        normalized = normalized[len('data/'):]

    if normalized.startswith('sessions/'):
        return os.path.join(DATA_ROOT, normalized)

    marker = '/data/'
    idx = normalized.lower().find(marker)
    if idx != -1:
        tail = normalized[idx + len(marker):]
        if tail.startswith('sessions/'):
            return os.path.join(DATA_ROOT, tail)

    return os.path.join(SESSIONS_ROOT, os.path.basename(normalized))

class SessionManager:
    def __init__(self):
        self.current_session_id = None
        self.current_session_folder = None

    def start_session(self, title=None):
        if self.current_session_id is not None:
            print("Une session est déjà en cours")
            return None

        if not title:
            title = f"Réunion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        folder_abs = os.path.join(SESSIONS_ROOT, title)
        folder_rel = f"sessions/{title}"
        os.makedirs(folder_abs, exist_ok=True)

        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO sessions (title, started_at, status, folder_path)
            VALUES (?, datetime('now'), 'recording', ?)
        """, (title, folder_rel))
        conn.commit()
        self.current_session_id = c.lastrowid
        self.current_session_folder = folder_abs
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
        merge_chunks(self.current_session_id, _resolve_session_folder(row['folder_path']))

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
        self.current_session_folder = None


# Test
if __name__ == "__main__":
    sm = SessionManager()
    sm.start_session()
    input("Appuie sur Entrée pour arrêter la session...")
    sm.stop_session()
    print("Vérifie dans DB Browser : tables sessions + jobs")
