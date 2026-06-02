import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
DB_PATH = os.path.join(DATA_DIR, 'stt_app.db')

# Audio
SAMPLE_RATE = 16000

# Whisper
WHISPER_MODEL = 'small'
WHISPER_LANGUAGE = 'fr'

# Pyannote
PYANNOTE_MODEL = 'pyannote/speaker-diarization-community-1'
HF_TOKEN = os.getenv('HF_TOKEN')


# Ollama
OLLAMA_URL = 'http://host.docker.internal:11434'
OLLAMA_MODEL = 'qwen3.5:4b'

# Paramètres spécifiques a ollama pour PV et résumé
PV_TEMPERATURE = 0.1
SUMMARY_TEMPERATURE = 0.3

PV_PREDICT = 500
SUMMARY_PREDICT = 500

PV_TIMEOUT = 500
SUMMARY_TIMEOUT = 500

GOLBAL_CTX = 4096

# Worker
POLL_INTERVAL = 10 # secondes entre chaque vérification des jobs

MAX_RETRY = 3 # Nombre maximum de tentatives pour un job avant de le marquer comme échoué

