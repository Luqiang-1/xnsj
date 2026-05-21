from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
VECTOR_DB_DIR = BASE_DIR / "app" / "data" / "vector_db"
