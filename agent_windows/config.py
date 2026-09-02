import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env.local'))

# Chemins
DATA_DIR = os.path.join(BASE_DIR, 'data')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
DB_PATH = os.path.join(DATA_DIR, 'stt_app.db')

# Audio
SAMPLE_RATE = 16000 # Hz — optimal pour Whisper
CHANNELS = 1 # mono
CHUNK_DURATION = 300 # secondes (5 min)
MAX_RECORDING_DURATION = 4 * 60 * 60 # secondes (4 h)
OLLAMA_PROXY_BIND = os.getenv('OLLAMA_PROXY_BIND', '0.0.0.0')
OLLAMA_PROXY_PORT = int(os.getenv('OLLAMA_PROXY_PORT', '11435'))
OLLAMA_PROXY_TOKEN = os.getenv('OLLAMA_PROXY_TOKEN', '')
OLLAMA_UPSTREAM_URL = os.getenv('OLLAMA_UPSTREAM_URL', 'http://127.0.0.1:11434').rstrip('/')

# Hotkey
HOTKEY = 'f12'

# Clé USB
USB_TARGET_LABEL = 'RESUMER'  # Label exact de la clé USB (insensible à la casse)
USB_VOLUME_SERIAL = os.getenv('USB_VOLUME_SERIAL', '').replace('-', '').upper()
USB_SECRET = os.getenv('USB_SECRET', '')
USB_SECRET_FILE = os.getenv('USB_SECRET_FILE', '.stt-usb-token')
USB_REQUIRE_BITLOCKER = os.getenv('USB_REQUIRE_BITLOCKER', 'true').lower() in ('1', 'true', 'yes', 'on')

# Bips
BIP_START_FREQ = 1000 # Hz — aigu = démarrage
BIP_START_DUR = 200 # ms
BIP_STOP_FREQ = 500 # Hz — grave = arrêt
BIP_STOP_DUR = 400 # ms
