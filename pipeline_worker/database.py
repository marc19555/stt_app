import sqlite3
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
from config import DB_PATH, MAX_RETRY as MAX_RETRIES


def _resolve_session_folder(folder_path):
    if not folder_path:
        return None

    normalized = str(folder_path).replace('\\', '/')

    if normalized.startswith('/app/data/'):
        return normalized

    if os.path.isabs(folder_path) and os.path.exists(folder_path):
        return folder_path

    relative = normalized.lstrip('/')
    if relative.startswith('data/'):
        relative = relative[len('data/'):]

    if relative.startswith('sessions/'):
        return os.path.join('/app/data', relative)

    marker = '/data/'
    idx = normalized.lower().find(marker)
    if idx != -1:
        tail = normalized[idx + len(marker):]
        if tail.startswith('sessions/'):
            return os.path.join('/app/data', tail)

    return os.path.join('/app/data', 'sessions', os.path.basename(relative))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def get_next_pending_job():
    """Récupère le prochain job à traiter"""
    conn = get_connection()
    job = conn.execute("""
        SELECT * FROM jobs
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
    """).fetchone()
    conn.close()
    return job

def set_job_status(job_id, status, error=None):
    """Met à jour le statut d'un job avec logique de retry"""
    conn = get_connection()

    if status == 'running':
        conn.execute("""
            UPDATE jobs SET status = ?, started_at = datetime('now')
            WHERE id = ?
        """, (status, job_id))

    elif status == 'done':
        conn.execute("""
            UPDATE jobs SET status = ?, finished_at = datetime('now')
            WHERE id = ?
        """, (status, job_id))

    elif status == 'failed':
        job = conn.execute(
            "SELECT retry_count FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

        if job and job['retry_count'] < MAX_RETRIES:
            conn.execute("""
                UPDATE jobs
                SET status = 'pending',
                    retry_count = retry_count + 1,
                    error_message = ?,
                    started_at = NULL
                WHERE id = ?
            """, (error, job_id))
            print(f"Job {job_id} remis en pending (tentative {job['retry_count']+1}/{MAX_RETRIES})")
        else:
            conn.execute("""
                UPDATE jobs
                SET status = 'failed',
                    finished_at = datetime('now'),
                    error_message = ?
                WHERE id = ?
            """, (error, job_id))
            print(f"Job {job_id} échoué définitivement après {MAX_RETRIES} tentatives")

    conn.commit()
    conn.close()

def set_session_status(session_id, status):
    """Met à jour le statut d'une session"""
    conn = get_connection()
    conn.execute("""
        UPDATE sessions SET status = ? WHERE id = ?
    """, (status, session_id))
    conn.commit()
    conn.close()

def get_session(session_id):
    """Récupère une session complète"""
    conn = get_connection()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return session

def save_artifact(session_id, artifact_type, file_path):
    """Enregistre un fichier produit en base"""
    conn = get_connection()
    conn.execute("""
        INSERT INTO artifacts (session_id, artifact_type, file_path)
        VALUES (?, ?, ?)
    """, (session_id, artifact_type, file_path))
    conn.commit()
    conn.close()


def archive_successful_session(session_id):
    """
    Archive une session terminee avec succes:
    - Supprime le dossier audio/ sur disque (gros fichiers WAV).
    - Conserve outputs/ et tous les JSON sur disque.
    - Supprime audio_chunks, jobs, artifacts, speakers en BDD.
    - Conserve la ligne session avec status='archived' pour l'historique.
    """
    conn = get_connection()
    session = conn.execute(
        "SELECT id, status, folder_path FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if session is None:
        conn.close()
        return False, "session introuvable"

    if session['status'] != 'done':
        conn.close()
        return False, f"statut non archivable: {session['status']}"

    # Nettoyage des lignes liees en BDD.
    conn.execute("DELETE FROM audio_chunks WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM artifacts  WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM speakers   WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM jobs       WHERE session_id = ?", (session_id,))

    # Conservation de la session avec status='archived' pour l'historique.
    # NOTE: le dossier audio/ est conserve sur disque pour verification qualite.
    conn.execute(
        "UPDATE sessions SET status = 'archived' WHERE id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()

    session_folder = _resolve_session_folder(session['folder_path'])
    return True, f"BDD nettoyee, audio/ conserve sur disque ({session_folder})"