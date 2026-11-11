from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENT_STORAGE_DIR = DATA_DIR / "documents"
BACKUP_DIR = BASE_DIR / "backups"
DB_PATH = DATA_DIR / "school_management.db"
APP_TITLE = "School Management System"

for directory in (DATA_DIR, BACKUP_DIR):
    directory.mkdir(parents=True, exist_ok=True)
