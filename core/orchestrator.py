# core/orchestrator.py
"""
Orchestrator: high-level glue that coordinates Analyzer, Cleaner, CryptoEngine,
StorageManager and ReportGenerator to ingest files into the encrypted vault and
to restore them by record id.
"""

from __future__ import annotations
import pathlib
import datetime
import base64
from typing import List

from .analyzer import Analyzer
from .cleaner import Cleaner
from .crypto_engine import CryptoEngine
from .storage_manager import StorageManager
from .report_generator import ReportGenerator


class Orchestrator:
    def __init__(self, db_path: str = "vault.db"):
        """
        Initialize subsystems. db_path may be a path string (absolute or relative)
        or left as default to let StorageManager choose a writable DB location.
        """
        self.analyzer = Analyzer()
        self.cleaner = Cleaner()
        self.crypto = CryptoEngine()
        self.storage = StorageManager(db_path)
        self.reporter = ReportGenerator()

    def ingest_path(self, path: str | pathlib.Path, passphrase: bytes | str):
        """
        Ingest a file or directory. If directory, recurses and ingests all files.
        passphrase may be bytes or str; str will be encoded as utf-8.
        """
        if isinstance(passphrase, str):
            passphrase_b = passphrase.encode()
        else:
            passphrase_b = passphrase

        p = pathlib.Path(path)
        targets: List[pathlib.Path] = []

        if p.is_dir():
            for child in p.rglob("*"):
                if child.is_file():
                    targets.append(child)
        elif p.is_file():
            targets = [p]
        else:
            print("[!] Path not found:", p)
            return

        for f in targets:
            try:
                print(f"[+] Processing {f}")
                # original file hash
                orig_hash = self.analyzer.hash_file(f)

                # extract metadata (may be empty dict)
                metadata = self.analyzer.extract_metadata(f)

                # remove metadata from bytes (returns bytes)
                cleaned_bytes = self.cleaner.remove_metadata_bytes(f, metadata)

                # hash of cleaned bytes
                cleaned_hash = self.analyzer.hash_bytes(cleaned_bytes)

                # encrypt cleaned bytes -> (salt, nonce, ciphertext)
                salt, nonce, ct = self.crypto.encrypt_bytes(cleaned_bytes, passphrase_b)

                # choose encrypted file name and store ciphertext bytes using storage manager
                enc_name = f"{f.name}.vault"
                enc_path = self.storage.save_encrypted_bytes(enc_name, ct)  # returns full path string

                # compute hash of the encrypted file (hash_file accepts path-like)
                enc_hash = self.analyzer.hash_file(pathlib.Path(enc_path))

                # timestamp in UTC (ISO 8601 with Z)
                timestamp = datetime.datetime.utcnow().isoformat() + "Z"

                # insert DB record (salt & nonce stored as raw bytes/BLOB)
                record_id = self.storage.insert_record(
                    original_name=f.name,
                    original_path=str(f.resolve()),
                    encrypted_name=pathlib.Path(enc_path).name,
                    salt=salt,
                    nonce=nonce,
                    original_sha256=orig_hash,
                    cleaned_sha256=cleaned_hash,
                    encrypted_sha256=enc_hash,
                    timestamp=timestamp
                )

                # prepare JSON-friendly payload for report (base64-encoded salt/nonce)
                payload = {
                    "original": str(f.resolve()),
                    "metadata_removed": list(metadata.keys()),
                    "original_sha256": orig_hash,
                    "cleaned_sha256": cleaned_hash,
                    "encrypted_sha256": enc_hash,
                    "vault_path": enc_path,
                    "timestamp": timestamp,
                    "salt": base64.b64encode(salt).decode() if salt else None,
                    "nonce": base64.b64encode(nonce).decode() if nonce else None
                }

                # generate report file (reporter handles pathing)
                self.reporter.generate_json_report(record_id, payload)

                print(f"[+] Stored ID {record_id}")

            except Exception as e:
                # don't crash the whole ingest loop for one file; report and continue
                print(f"[!] Failed processing {f}: {e}")

    def restore_id(self, record_id: int, passphrase: bytes | str, out_folder: str | pathlib.Path):
        """
        Restore a record by id. Reads DB record, fetches encrypted file, decrypts with passphrase,
        and writes plaintext to out_folder using original filename.
        """
        if isinstance(passphrase, str):
            passphrase_b = passphrase.encode()
        else:
            passphrase_b = passphrase

        rec = self.storage.get_record(record_id)
        if not rec:
            print("[!] Record not found:", record_id)
            return

        try:
            enc_name = rec.get("encrypted_name")
            enc_path = self.storage.get_encrypted_path(enc_name)
        except Exception as e:
            print("[!] Could not locate encrypted file for record:", record_id, "error:", e)
            return

        try:
            with open(enc_path, "rb") as f:
                ct = f.read()
        except Exception as e:
            print("[!] Failed to read encrypted file:", enc_path, "error:", e)
            return

        try:
            # rec['salt'] and rec['nonce'] are stored as BLOBs (bytes)
            salt = rec.get("salt")
            nonce = rec.get("nonce")
            pt = self.crypto.decrypt_bytes(ct, passphrase_b, salt, nonce)
        except Exception as e:
            print("[!] Decryption failed:", e)
            return

        out_folder = pathlib.Path(out_folder)
        out_folder.mkdir(parents=True, exist_ok=True)
        out_file = out_folder / rec.get("original_name", f"restored_{record_id}")

        try:
            with open(out_file, "wb") as f:
                f.write(pt)
            print("[+] Restored to", out_file)
        except Exception as e:
            print("[!] Failed to write restored file:", e)
