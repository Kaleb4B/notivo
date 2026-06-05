import os
from pathlib import Path

APP_NAME = "Notivo"
APP_VERSION = "1.0.0"

# Default paths
DEFAULT_DOCUMENTS_DIR = Path.home() / "Documents"
DEFAULT_SESSIONS_DIR = DEFAULT_DOCUMENTS_DIR / "Notivo_Sessions"
APP_DATA_DIR = Path.home() / ".notivo"
CONFIG_FILE = APP_DATA_DIR / "config.json"
LOG_FILE = APP_DATA_DIR / "notivo.log"

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_MS = 500  # ms
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

# VAD parameters
VAD_THRESHOLD = 0.5
