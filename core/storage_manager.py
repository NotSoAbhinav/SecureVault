# core/storage_manager.py
import sqlite3
from pathlib import Path
import traceback
import sqlite3
from core.utils import resource_path, ensure_writable_db, user_data_dir

class StorageManager:
    def __init__(self, db_path: str = None):
        """
        db_path: optional explicit path. If None, ensure_writable_db() will provide a per-user writable DB.
        """
        # If explicit path provided and exists as string, use it. Otherwise ensure a writable db.
        if db_path and Path(db_path).is_absolute():
            self.db_file = Path(db_path)
        else:
            # ensures a writable DB in user data dir (copies bundled DB or creates from schema)
            self.db_file = ensure_writable_db(bundle_db_path="vault.db", db_name="vault.db")
        # Init DB (run schema if necessary)
        self._init_db()

    def _init_db(self):
        """Make sure tables exist. If db already has tables this is no-op."""
        schema_path = resource_path("db/schema.sql")
        conn = sqlite3.connect(self.db_file)
        try:
            # If schema.sql exists, run it (safe)
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            # else, assume DB already OK. Optionally verify tables:
            # You can also check for a table and create minimal one if missing.
        finally:
            conn.commit()
            conn.close()

    def save_encrypted_bytes(self, filename: str, data: bytes) -> str:
        """Save encrypted bytes into a vault_store directory under user_data_dir and return full path."""
        try:
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError("save_encrypted_bytes expects bytes")

            vault_dir = user_data_dir() / "vault_store"
            vault_dir.mkdir(parents=True, exist_ok=True)

            safe_name = Path(filename).name
            target = vault_dir / safe_name

            # avoid name collision
            if target.exists():
                base = target.stem
                suf = target.suffix
                i = 1
                while True:
                    candidate = vault_dir / f"{base}_{i}{suf}"
                    if not candidate.exists():
                        target = candidate
                        break
                    i += 1

            with open(target, "wb") as f:
                f.write(data)

            return str(target.resolve())

        except Exception:
            # log for debugging
            logf = user_data_dir() / "last_error.log"
            with open(logf, "w", encoding="utf-8") as lf:
                lf.write("Error in save_encrypted_bytes:\n")
                traceback.print_exc(file=lf)
            raise

    def insert_record(self,
                      original_name: str,
                      original_path: str,
                      encrypted_name: str,
                      salt: bytes,
                      nonce: bytes,
                      original_sha256: str,
                      cleaned_sha256: str,
                      encrypted_sha256: str,
                      timestamp: str) -> int:
        """
        Insert a row, storing salt/nonce as BLOBs. Returns inserted row id.
        """
        conn = sqlite3.connect(self.db_file)
        try:
            c = conn.cursor()
            c.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT,
                original_path TEXT,
                encrypted_name TEXT,
                salt BLOB,
                nonce BLOB,
                original_sha256 TEXT,
                cleaned_sha256 TEXT,
                encrypted_sha256 TEXT,
                timestamp TEXT
            );
            """)
            c.execute("""
            INSERT INTO records
            (original_name, original_path, encrypted_name, salt, nonce, original_sha256, cleaned_sha256, encrypted_sha256, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                original_name,
                original_path,
                encrypted_name,
                sqlite3.Binary(salt) if salt is not None else None,
                sqlite3.Binary(nonce) if nonce is not None else None,
                original_sha256,
                cleaned_sha256,
                encrypted_sha256,
                timestamp
            ))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()

    def get_record(self, record_id: int):
        """Return a dict for a record or None if not found. salt/nonce returned as bytes (BLOB)."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM records WHERE id = ?", (record_id,))
            row = c.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    def get_encrypted_path(self, encrypted_name: str) -> str:
        """
        Search for an encrypted_name under the user vault_store and return absolute path if found.
        This assumes save_encrypted_bytes saved it under user_data_dir()/vault_store.
        """
        vault_dir = user_data_dir() / "vault_store"
        candidate = vault_dir / encrypted_name
        if candidate.exists():
            return str(candidate.resolve())
        # try fallback: if encoder appended suffix _1 etc, find first matching prefix
        for p in vault_dir.iterdir() if vault_dir.exists() else []:
            if p.name.startswith(Path(encrypted_name).stem):
                return str(p.resolve())
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_name}")
