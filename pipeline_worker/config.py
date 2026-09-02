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
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'fr')

# Pyannote
PYANNOTE_MODEL = 'pyannote/speaker-diarization-community-1'
HF_TOKEN = os.getenv('HF_TOKEN')
DIARIZATION_ENABLED = os.getenv('DIARIZATION_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on')


# Ollama
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11435').rstrip('/')
OLLAMA_PROXY_TOKEN = os.getenv('OLLAMA_PROXY_TOKEN', '')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'granite4.1:3b')
OLLAMA_FALLBACK_MODEL = os.getenv('OLLAMA_FALLBACK_MODEL', 'qwen3.5:0.8b')

# Paramètres spécifiques a ollama pour PV et résumé
PV_TEMPERATURE = 0.1
SUMMARY_TEMPERATURE = 0.3

PV_PREDICT = int(os.getenv('OLLAMA_NUM_PREDICT', '2048'))
SUMMARY_PREDICT = int(os.getenv('OLLAMA_NUM_PREDICT', '2048'))

PV_TIMEOUT = 500000
SUMMARY_TIMEOUT = 500000

GLOBAL_CTX = int(os.getenv('OLLAMA_NUM_CTX', '8192'))

# Worker
POLL_INTERVAL = 10 # secondes entre chaque vérification des jobs

MAX_RETRY = 3 # Nombre maximum de tentatives pour un job avant de le marquer comme échoué

DOCUMENT_RETENTION_DAYS = int(os.getenv('DOCUMENT_RETENTION_DAYS', '7'))



