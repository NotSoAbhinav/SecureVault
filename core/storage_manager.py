# core/storage_manager.py
from pathlib import Path
from core.utils import resource_path, ensure_writable_db

class StorageManager:
    def __init__(self, db_path: str = None):
        # prefer explicit db_path param, else ensure a user-writable DB
        if db_path:
            self.db_file = Path(db_path)
        else:
            # this will copy bundled vault.db to AppData or create from schema
            self.db_file = ensure_writable_db(bundle_db_path="vault.db", db_name="vault.db")
        self._init_db()

    def _init_db(self):
        # Use sqlite3 to open and if empty run schema; if you already copied schema, this will be no-op
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        # optionally verify tables exist, or run schema if empty
        # ... your existing logic ...
        conn.close()
