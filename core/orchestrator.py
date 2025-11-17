import os
import pathlib
from .analyzer import Analyzer
from .cleaner import Cleaner
from .crypto_engine import CryptoEngine
from .storage_manager import StorageManager
from .report_generator import ReportGenerator
import datetime

class Orchestrator:
    def __init__(self, db_path="vault.db"):
        self.analyzer = Analyzer()
        self.cleaner = Cleaner()
        self.crypto = CryptoEngine()
        self.storage = StorageManager(db_path)
        self.reporter = ReportGenerator()

    def ingest_path(self, path, passphrase):
        path = pathlib.Path(path)
        targets = []
        if path.is_dir():
            for p in path.rglob("*"):
                if p.is_file():
                    targets.append(p)
        elif path.is_file():
            targets = [path]
        else:
            print("Path not found:", path)
            return

        for f in targets:
            print(f"[+] Processing {f}")
            orig_hash = self.analyzer.hash_file(f)
            metadata = self.analyzer.extract_metadata(f)
            cleaned_bytes = self.cleaner.remove_metadata_bytes(f, metadata)
            cleaned_hash = self.analyzer.hash_bytes(cleaned_bytes)
            salt, nonce, ct = self.crypto.encrypt_bytes(cleaned_bytes, passphrase.encode())
            enc_name = f"{f.name}.vault"
            enc_path = self.storage.save_encrypted_bytes(enc_name, ct)
            enc_hash = self.analyzer.hash_file(enc_path)
            timestamp = datetime.datetime.utcnow().isoformat() + "Z"
            record_id = self.storage.insert_record(
                original_name=f.name,
                original_path=str(f),
                encrypted_name=enc_name,
                salt=salt,
                nonce=nonce,
                original_sha256=orig_hash,
                cleaned_sha256=cleaned_hash,
                encrypted_sha256=enc_hash,
                timestamp=timestamp
            )
            self.reporter.generate_json_report(record_id, {
                "original": str(f),
                "metadata_removed": list(metadata.keys()),
                "original_sha256": orig_hash,
                "cleaned_sha256": cleaned_hash,
                "encrypted_sha256": enc_hash,
                "vault_path": enc_path,
                "timestamp": timestamp
            })
            print(f"[+] Stored ID {record_id}")

    def restore_id(self, record_id, passphrase, out_folder):
        rec = self.storage.get_record(record_id)
        if not rec:
            print("Record not found:", record_id)
            return
        enc_path = self.storage.get_encrypted_path(rec["encrypted_name"])
        with open(enc_path, "rb") as f:
            ct = f.read()
        try:
            pt = self.crypto.decrypt_bytes(ct, passphrase.encode(), rec["salt"], rec["nonce"])
        except Exception as e:
            print("Decryption failed:", e)
            return
        out_folder = pathlib.Path(out_folder)
        out_folder.mkdir(parents=True, exist_ok=True)
        out_file = out_folder / rec["original_name"]
        with open(out_file, "wb") as f:
            f.write(pt)
        print("[+] Restored to", out_file)
