import os

# Chemins
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
DB_PATH = os.path.join(DATA_DIR, 'stt_app.db')

# Audio
SAMPLE_RATE = 16000 # Hz — optimal pour Whisper
CHANNELS = 1 # mono
CHUNK_DURATION = 300 # secondes (5 min)
MAX_RECORDING_DURATION = 4 * 60 * 60 # secondes (4 h)
HOST_RAM_SERVER_PORT = int(os.getenv('HOST_RAM_SERVER_PORT', '8765'))

# Hotkey
HOTKEY = 'f12'

# Bips
BIP_START_FREQ = 1000 # Hz — aigu = démarrage
BIP_START_DUR = 200 # ms
BIP_STOP_FREQ = 500 # Hz — grave = arrêt
BIP_STOP_DUR = 400 # ms