CREATE TABLE IF NOT EXISTS vault_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_name TEXT NOT NULL,
  original_path TEXT,
  encrypted_name TEXT NOT NULL,
  salt BLOB NOT NULL,
  nonce BLOB NOT NULL,
  original_sha256 TEXT NOT NULL,
  cleaned_sha256 TEXT NOT NULL,
  encrypted_sha256 TEXT NOT NULL,
  timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
