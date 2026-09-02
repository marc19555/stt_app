import sqlite3
import os
import sys
import shutil

sys.path.append(os.path.dirname(__file__))
from config import DATA_DIR, DB_PATH, MAX_RETRY as MAX_RETRIES


def _resolve_session_folder(folder_path):
    if not folder_path:
        return None

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

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Cree le schema aussi depuis Docker si l'agent n'a pas encore demarre."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT,
            created_at TEXT DEFAULT (datetime('now')), started_at TEXT,
            stopped_at TEXT, status TEXT DEFAULT 'recording', folder_path TEXT,
            audio_final_path TEXT, duration_seconds INTEGER, error_message TEXT
        );
        CREATE TABLE IF NOT EXISTS audio_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            chunk_index INTEGER, file_path TEXT, started_at TEXT, ended_at TEXT,
            duration_seconds INTEGER, status TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id), job_type TEXT,
            status TEXT DEFAULT 'pending', priority INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')), started_at TEXT,
            finished_at TEXT, retry_count INTEGER DEFAULT 0, error_message TEXT
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            artifact_type TEXT, file_path TEXT
        );
        CREATE TABLE IF NOT EXISTS speakers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            speaker_label TEXT, display_name TEXT, role TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_queue
            ON jobs(status, priority DESC, created_at ASC);
    """)
    conn.commit()
    conn.close()


def claim_next_pending_job():
    """Reserve atomiquement un job pour eviter deux traitements simultanes."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        candidate = conn.execute("""
            SELECT id FROM jobs WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC LIMIT 1
        """).fetchone()
        if candidate is None:
            conn.commit()
            return None
        updated = conn.execute("""
            UPDATE jobs SET status = 'running', started_at = datetime('now'),
                error_message = NULL
            WHERE id = ? AND status = 'pending'
        """, (candidate['id'],))
        if updated.rowcount != 1:
            conn.rollback()
            return None
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (candidate['id'],)).fetchone()
        conn.commit()
        return job
    finally:
        conn.close()


def recover_stuck_jobs():
    """Remet en file les jobs laisses running par un arret brutal."""
    conn = get_connection()
    recoverable = conn.execute(
        "SELECT id, session_id FROM jobs WHERE status = 'running' AND retry_count < ?",
        (MAX_RETRIES,),
    ).fetchall()
    exhausted = conn.execute(
        "SELECT id, session_id FROM jobs WHERE status = 'running' AND retry_count >= ?",
        (MAX_RETRIES,),
    ).fetchall()
    for row in recoverable:
        conn.execute("""
            UPDATE jobs SET status='pending', retry_count=retry_count+1,
                started_at=NULL, error_message='Reprise apres interruption brutale'
            WHERE id=?
        """, (row['id'],))
        conn.execute(
            "UPDATE sessions SET status='recording_done' WHERE id=?",
            (row['session_id'],),
        )
    for row in exhausted:
        conn.execute("""
            UPDATE jobs SET status='failed', finished_at=datetime('now'),
                error_message='Nombre maximal de reprises atteint'
            WHERE id=?
        """, (row['id'],))
        conn.execute("UPDATE sessions SET status='failed' WHERE id=?", (row['session_id'],))
    conn.commit()
    conn.close()
    return len(recoverable), len(exhausted)

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
    - Supprime audio, chunks et JSON intermediaires.
    - Conserve seulement les documents produits, jusqu'a la purge de retention.
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

    session_folder = _resolve_session_folder(session['folder_path'])
    removed = []
    for name in ('audio', 'transcription', 'diarization', 'merged'):
        target = os.path.join(session_folder, name)
        if os.path.isdir(target):
            try:
                shutil.rmtree(target)
                removed.append(name)
            except OSError as exc:
                conn.close()
                return False, f"suppression de {name} impossible: {exc}"

    # Nettoyage des lignes liees en BDD apres suppression confirmee sur disque.
    conn.execute("DELETE FROM audio_chunks WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM artifacts  WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM speakers   WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM jobs       WHERE session_id = ?", (session_id,))
    conn.execute(
        "UPDATE sessions SET status = 'archived', audio_final_path = NULL WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()
    return True, "intermediaires supprimes: " + (", ".join(removed) or "aucun")


def purge_expired_sessions(retention_days):
    """Supprime les documents et lignes BDD plus anciens que la retention."""
    if retention_days < 1:
        raise ValueError("La retention doit etre d'au moins un jour")
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, folder_path FROM sessions
        WHERE status IN ('archived', 'done')
          AND datetime(COALESCE(stopped_at, created_at)) < datetime('now', ?)
    """, (f'-{retention_days} days',)).fetchall()
    purged = 0
    for row in rows:
        folder = _resolve_session_folder(row['folder_path'])
        try:
            if folder and os.path.isdir(folder):
                shutil.rmtree(folder)
        except OSError as exc:
            print(f"Purge reportee pour session {row['id']}: {exc}")
            continue
        for table in ('audio_chunks', 'artifacts', 'speakers', 'jobs'):
            conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (row['id'],))
        conn.execute("DELETE FROM sessions WHERE id = ?", (row['id'],))
        purged += 1
    conn.commit()
    conn.close()
    return purged
