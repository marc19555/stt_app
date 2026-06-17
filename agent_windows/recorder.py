import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import sys
import threading
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
from config import SAMPLE_RATE, CHANNELS, CHUNK_DURATION, DATA_DIR
import database as db

def has_audio_input_device() -> bool:
    """Vérifie si au moins un périphérique d'entrée audio est détecté."""
    try:
        # Réinitialise PortAudio pour actualiser la liste des périphériques USB branchés à chaud
        try:
            sd._terminate()
            sd._initialize()
        except Exception as e:
            print(f"[WARNING] Impossible de réinitialiser sounddevice : {e}")

        devices = sd.query_devices()
        return any(d.get('max_input_channels', 0) > 0 for d in devices)
    except Exception as e:
        print(f"[ERREUR] Échec de la recherche de périphériques audio : {e}")
        return False

class Recorder:
    def __init__(self, session_folder, session_id, on_error_callback=None):
        self.session_folder: str = session_folder
        self.session_id: int = session_id
        self.is_recording: bool = False
        self.frames: list = []
        self.chunk_index: int = 0
        self.thread = None
        self.on_error_callback = on_error_callback

    def start(self):
        os.makedirs(self.session_folder, exist_ok=True)
        self.is_recording = True
        self.frames = []
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.start()
        print("Enregistrement démarré")

    def stop(self):
        self.is_recording = False
        if self.thread:
            self.thread.join()
        print("Enregistrement arrêté")

    def _record_loop(self):
        chunk_frames = []
        chunk_start = datetime.now()

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32') as stream:
                while self.is_recording:
                    data, _ = stream.read(SAMPLE_RATE)
                    chunk_frames.append(data)

                    elapsed = (datetime.now() - chunk_start).seconds
                    if elapsed >= CHUNK_DURATION:
                        chunk_end = datetime.now()
                        audio = np.concatenate(chunk_frames, axis=0)
                        self._save_chunk(audio, chunk_start, chunk_end, elapsed)
                        chunk_frames = []
                        chunk_start = datetime.now()

            # Sauvegarde le reste à l'arrêt
            if chunk_frames:
                chunk_end = datetime.now()
                elapsed = (chunk_end - chunk_start).seconds
                audio = np.concatenate(chunk_frames, axis=0)
                self._save_chunk(audio, chunk_start, chunk_end, elapsed)
        except Exception as e:
            print(f"[ERREUR] Le flux d'enregistrement a rencontré une erreur : {e}")
            if self.on_error_callback:
                self.on_error_callback(str(e))

    def _save_chunk(self, audio=None, start_time=None, end_time=None, duration=None):
        if audio is None:
            return None

        filename = f"chunk_{self.chunk_index:03d}.wav"
        audio_folder = os.path.join(self.session_folder, 'audio')
        os.makedirs(audio_folder, exist_ok=True)
        filepath = os.path.join(audio_folder, filename)
        sf.write(filepath, audio, SAMPLE_RATE)
        relative_path = os.path.relpath(filepath, DATA_DIR).replace('\\', '/')

        conn = db.get_connection()
        conn.execute("""
            INSERT INTO audio_chunks (session_id, chunk_index, file_path, started_at, ended_at, duration_seconds, status)
            VALUES (?, ?, ?, ?, ?, ?, 'done')
        """, (self.session_id, self.chunk_index, relative_path, start_time, end_time, duration))
        conn.commit()
        conn.close()

        print(f"Chunk sauvegardé : {filename} ({duration:.2f}s)")
        self.chunk_index += 1
        return filepath