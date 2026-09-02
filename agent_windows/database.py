import sqlite3
import os
import sys

sys.path.append(os.path.dirname(__file__))
from config import DB_PATH

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            stopped_at TEXT,
            status TEXT DEFAULT 'recording',
            folder_path TEXT,
            audio_final_path TEXT,
            duration_seconds INTEGER,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS audio_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            chunk_index INTEGER,
            file_path TEXT,
            started_at TEXT,
            ended_at TEXT,
            duration_seconds INTEGER,
            status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            job_type TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            finished_at TEXT,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            artifact_type TEXT,
            file_path TEXT
        );

        CREATE TABLE IF NOT EXISTS speakers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            speaker_label TEXT,
            display_name TEXT,
            role TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_queue
            ON jobs(status, priority DESC, created_at ASC);
    """)

    conn.commit()
    conn.close()
    print(f"Base créée : {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    init_db()
