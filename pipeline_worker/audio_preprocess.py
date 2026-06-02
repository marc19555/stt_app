import os
import sys
import numpy as np
import soundfile as sf

sys.path.append(os.path.dirname(__file__))
from config import SAMPLE_RATE
import database as db


def _resolve_chunk_path_for_docker(path_value):
    if not path_value:
        return None

    normalized = str(path_value).replace('\\', '/')

    if normalized.startswith('/app/data/'):
        return normalized

    if os.path.isabs(normalized) and os.path.exists(normalized):
        return normalized

    normalized = normalized.lstrip('/')
    if normalized.startswith('data/'):
        normalized = normalized[len('data/'):]

    return os.path.join('/app/data', normalized)

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
    
    all_audio = []
    for row in rows:
        # Chemin absolu Linux dans le conteneur pour lire les morceaux
        full_chunk_path = _resolve_chunk_path_for_docker(row['file_path'])
        
        if os.path.exists(full_chunk_path):
            data, _ = sf.read(full_chunk_path)
            all_audio.append(data)
        else:
            print(f"Chunk manquant : {full_chunk_path}")
            
    if not all_audio:
        raise Exception("Tous les chunks sont manquants")
        
    final_audio = np.concatenate(all_audio, axis=0)
    
    # 3. Chemin absolu Linux pour écrire le fichier final combiné
    final_path = os.path.join(docker_audio_folder, 'final.wav')
    sf.write(final_path, final_audio, SAMPLE_RATE)
    
    # Met à jour la session en BDD
    conn = db.get_connection()
    conn.execute("""
        UPDATE sessions SET audio_final_path = ? WHERE id = ?
    """, (final_path, session_id))
    conn.commit()
    conn.close()
    
    print(f"Reconstruit : {final_path}")
    return final_path