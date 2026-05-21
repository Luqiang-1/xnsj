from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "agri-rag-system" / "knowledge"
STATIC_DIR = BASE_DIR / "static"

HOST = "127.0.0.1"
PORT = 8000

MAX_CONTEXTS = 5
MIN_SCORE = 2
