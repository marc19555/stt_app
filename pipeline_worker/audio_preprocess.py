import os
import sys
import soundfile as sf

sys.path.append(os.path.dirname(__file__))
from config import DATA_DIR, SAMPLE_RATE
import database as db


def _resolve_chunk_path_for_docker(path_value):
    if not path_value:
        return None

    normalized = str(path_value).replace('\\', '/')

    if normalized.startswith('/app/data/'):
        candidate = os.path.join(DATA_DIR, *normalized[len('/app/data/'):].split('/'))
    elif os.path.isabs(normalized) and os.path.exists(normalized):
        candidate = normalized
    else:
        normalized = normalized.lstrip('/')
        if normalized.startswith('data/'):
            normalized = normalized[len('data/'):]
        candidate = os.path.join(DATA_DIR, *normalized.split('/'))

    candidate = os.path.realpath(candidate)
    if os.path.commonpath((os.path.realpath(DATA_DIR), candidate)) != os.path.realpath(DATA_DIR):
        raise ValueError("Chemin audio hors du dossier data")
    return candidate

def prepare_audio(session_id, session_folder):
    """
    Récupère le final.wav déjà créé par l'agent Windows.
    Si absent, reconstruit depuis les chunks en base.
    Retourne le chemin du fichier audio prêt pour Whisper.
    """
    audio_folder = os.path.join(session_folder, 'audio')
    final_path = os.path.join(audio_folder, 'final.wav')

    # Cas normal : final.wav existe déjà
    if os.path.exists(final_path):
        print(f"final.wav trouvé : {final_path}")
        return final_path

    # Fallback : reconstruit depuis les chunks
    print("final.wav absent, reconstruction depuis chunks...")
    final_path = _rebuild_from_chunks(session_id, audio_folder)
    return final_path

def _rebuild_from_chunks(session_id, audio_folder):
    # 1. On extrait le nom du dossier de session (ex: Réunion_20260601_112249)
    session_name = os.path.basename(os.path.normpath(os.path.dirname(audio_folder)))
    
    # 2. On reconstruit le dossier cible correct pour Docker
    docker_audio_folder = os.path.join('/app/data', 'sessions', session_name, 'audio')
    os.makedirs(docker_audio_folder, exist_ok=True)
    
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT file_path FROM audio_chunks
        WHERE session_id = ?
        ORDER BY chunk_index ASC
    """, (session_id,)).fetchall()
    conn.close()
    
    if not rows:
        raise Exception("Aucun chunk audio trouvé en base")
    
    final_path = os.path.join(docker_audio_folder, 'final.wav')
    frames_written = 0
    with sf.SoundFile(
        final_path, mode='w', samplerate=SAMPLE_RATE, channels=1, subtype='PCM_16'
    ) as destination:
        for row in rows:
            full_chunk_path = _resolve_chunk_path_for_docker(row['file_path'])
            if not full_chunk_path or not os.path.exists(full_chunk_path):
                print(f"Chunk manquant : {full_chunk_path}")
                continue
            with sf.SoundFile(full_chunk_path, mode='r') as source:
                if source.samplerate != SAMPLE_RATE or source.channels != 1:
                    raise ValueError(f"Format audio incompatible: {os.path.basename(full_chunk_path)}")
                while True:
                    block = source.read(65536, dtype='float32', always_2d=True)
                    if len(block) == 0:
                        break
                    destination.write(block)
                    frames_written += len(block)

    if frames_written == 0:
        try:
            os.remove(final_path)
        except FileNotFoundError:
            pass
        raise Exception("Tous les chunks sont manquants")
    
    # Met à jour la session en BDD
    conn = db.get_connection()
    conn.execute("""
        UPDATE sessions SET audio_final_path = ? WHERE id = ?
    """, (final_path, session_id))
    conn.commit()
    conn.close()
    
    print(f"Audio reconstruit en flux : {final_path}")
    return final_path
