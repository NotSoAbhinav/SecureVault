# core/utils.py
import sys
from pathlib import Path
import shutil
import os
import appdirs

def resource_path(rel_path: str) -> Path:
    
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent  # project root
    return (base / rel_path).resolve()

def user_data_dir(app_name: str = "SecureVault") -> Path:
   
    p = Path(appdirs.user_data_dir(app_name))
    p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_writable_db(bundle_db_path: str = "vault.db", db_name: str = "vault.db") -> Path:
   
    user_dir = user_data_dir()
    target_db = user_dir / db_name
    if target_db.exists():
        return target_db

    try:
        bundled = resource_path(bundle_db_path)
        if bundled.exists():
            shutil.copyfile(bundled, target_db)
            return target_db
    except Exception:
        pass

    schema = resource_path("db/schema.sql")
    import sqlite3
    conn = sqlite3.connect(target_db)
    if schema.exists():
        with open(schema, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()
    return target_db
