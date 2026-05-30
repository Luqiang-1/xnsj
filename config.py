from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "agri-rag-system" / "knowledge"
STATIC_DIR = BASE_DIR / "static"
APP_DATA_DIR = BASE_DIR / "data" / "app_state"
USERS_FILE = APP_DATA_DIR / "users.json"
COMMUNITY_FILE = APP_DATA_DIR / "community.json"

HOST = "127.0.0.1"
PORT = 8000

MAX_CONTEXTS = 5
MIN_SCORE = 2

AUTH_COOKIE_NAME = "crop_forum_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 14
