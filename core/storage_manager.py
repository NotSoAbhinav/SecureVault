from pathlib import Path
import sqlite3
import os

class StorageManager:
    def __init__(self, db_path="vault.db", vault_folder="vault_store"):
        # Base directory = project root (two levels up from this file)
        self.base_dir = Path(__file__).resolve().parent.parent

        # Force absolute paths inside project root
        self.db_path = self.base_dir / db_path
        self.vault_folder = self.base_dir / vault_folder

        self.vault_folder.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        schema_path = self.base_dir / "db" / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executescript(schema)
        conn.commit()
        conn.close()

    def save_encrypted_bytes(self, filename, bytes_data):
        path = self.vault_folder / filename
        with open(path, "wb") as f:
            f.write(bytes_data)
        return str(path)

    def insert_record(self, original_name, original_path, encrypted_name, salt, nonce,
                      original_sha256, cleaned_sha256, encrypted_sha256, timestamp):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO vault_files
            (original_name, original_path, encrypted_name, salt, nonce,
             original_sha256, cleaned_sha256, encrypted_sha256, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (original_name, original_path, encrypted_name, salt, nonce,
              original_sha256, cleaned_sha256, encrypted_sha256, timestamp))
        conn.commit()
        rowid = c.lastrowid
        conn.close()
        return rowid

    def get_record(self, record_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM vault_files WHERE id = ?", (record_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def get_encrypted_path(self, encrypted_name):
        return str(self.vault_folder / encrypted_name)
