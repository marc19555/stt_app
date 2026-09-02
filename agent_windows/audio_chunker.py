import os
import sys
import soundfile as sf

sys.path.append(os.path.dirname(__file__))
from config import SAMPLE_RATE, DATA_DIR
import database as db


def _resolve_data_path(path_value):
    if not path_value:
        return None

    if os.path.isabs(path_value):
        candidate = os.path.realpath(path_value)
    else:
        normalized = str(path_value).replace('\\', '/').lstrip('/')
        if normalized.startswith('data/'):
            normalized = normalized[len('data/'):]
        candidate = os.path.realpath(os.path.join(DATA_DIR, *normalized.split('/')))
    if os.path.commonpath((os.path.realpath(DATA_DIR), candidate)) != os.path.realpath(DATA_DIR):
        raise ValueError("Chemin audio hors du dossier data")
    return candidate

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

    final_path = os.path.join(audio_folder, 'final.wav')
    frames_written = 0
    found = False
    # Ecriture bloc par bloc : la RAM reste constante, meme pour quatre heures.
    with sf.SoundFile(
        final_path, mode='w', samplerate=SAMPLE_RATE, channels=1, subtype='PCM_16'
    ) as destination:
        for row in rows:
            chunk_path = _resolve_data_path(row['file_path'])
            if not chunk_path or not os.path.exists(chunk_path):
                print(f"Chunk manquant : {row['file_path']}")
                continue
            found = True
            with sf.SoundFile(chunk_path, mode='r') as source:
                if source.samplerate != SAMPLE_RATE or source.channels != 1:
                    raise ValueError(f"Format audio incompatible: {os.path.basename(chunk_path)}")
                while True:
                    block = source.read(65536, dtype='float32', always_2d=True)
                    if len(block) == 0:
                        break
                    destination.write(block)
                    frames_written += len(block)

    if not found:
        try:
            os.remove(final_path)
        except FileNotFoundError:
            pass
        return None

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

    duration = frames_written / SAMPLE_RATE
    print(f"Fichier final créé : {final_path} ({duration:.1f}s)")
    return final_path
