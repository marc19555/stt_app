import os
import sys
import numpy as np
import soundfile as sf

sys.path.append(os.path.dirname(__file__))
from config import SAMPLE_RATE, DATA_DIR
import database as db


def _resolve_data_path(path_value):
    if not path_value:
        return None

    if os.path.isabs(path_value):
        return path_value

    normalized = str(path_value).replace('\\', '/').lstrip('/')
    if normalized.startswith('data/'):
        normalized = normalized[len('data/'):]
    return os.path.join(DATA_DIR, normalized)

def merge_chunks(session_id, session_folder):
    """
    Fusionne tous les chunks WAV en un seul fichier final.wav
    Retourne le chemin du fichier final.
    """
    audio_folder = os.path.join(session_folder, 'audio')
    os.makedirs(audio_folder, exist_ok=True)

    # Récupère les chunks depuis la DB, dans l'ordre
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT file_path FROM audio_chunks
        WHERE session_id = ?
        ORDER BY chunk_index ASC
    """, (session_id,)).fetchall()
    conn.close()

    if not rows:
        print("Aucun chunk trouvé pour cette session")
        return None

    # Concatène les fichiers audio
    all_audio = []
    for row in rows:
        chunk_path = _resolve_data_path(row['file_path'])
        if chunk_path and os.path.exists(chunk_path):
            data, _ = sf.read(chunk_path)
            all_audio.append(data)
        else:
            print(f"Chunk manquant : {row['file_path']}")

    if not all_audio:
        return None

    final_audio = np.concatenate(all_audio, axis=0)
    final_path = os.path.join(audio_folder, 'final.wav')
    sf.write(final_path, final_audio, SAMPLE_RATE)

    # Met à jour la session en base
    conn = db.get_connection()
    final_path_rel = os.path.relpath(final_path, DATA_DIR).replace('\\', '/')
    conn.execute("""
        UPDATE sessions
        SET audio_final_path = ?
        WHERE id = ?
    """, (final_path_rel, session_id))
    conn.commit()
    conn.close()

    duration = len(final_audio) / SAMPLE_RATE
    print(f"Fichier final créé : {final_path} ({duration:.1f}s)")
    return final_path