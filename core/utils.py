# core/utils.py
import sys
from pathlib import Path
import shutil
import os
import appdirs

def resource_path(rel_path: str) -> Path:
    """
    Return absolute path to resource packaged by PyInstaller (onefile/onedir) or dev path.
    For read-only files included in the exe (like db/schema.sql or example files).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent  # project root
    return (base / rel_path).resolve()

def user_data_dir(app_name: str = "SecureVault") -> Path:
    """
    Return a folder in which to store writable files (DB, vault_store, reports).
    Uses OS-appropriate per-user location.
    """
    p = Path(appdirs.user_data_dir(app_name))
    p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_writable_db(bundle_db_path: str = "vault.db", db_name: str = "vault.db") -> Path:
    """
    Ensure a writable DB exists in user data dir. If not present, copy bundled DB or
    create a new DB using schema.sql if bundled DB missing.
    Returns path to writable DB file.
    """
    user_dir = user_data_dir()
    target_db = user_dir / db_name
    if target_db.exists():
        return target_db

    # Try to copy bundled DB (if you included vault.db in add-data)
    try:
        bundled = resource_path(bundle_db_path)
        if bundled.exists():
            shutil.copyfile(bundled, target_db)
            return target_db
    except Exception:
        pass

    # Otherwise, create DB from schema.sql (if present in bundle)
    schema = resource_path("db/schema.sql")
    import sqlite3
    conn = sqlite3.connect(target_db)
    if schema.exists():
        with open(schema, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()
    return target_db
