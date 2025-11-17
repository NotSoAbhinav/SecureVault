# Secure File Vault — Encryption & Metadata Removal

**Short:** A Secure desktop tool that strips hidden metadata from files, encrypts them (AES-256-GCM), stores them in a local vault and generates tamper-evident forensic reports.

## Features
- Batch file ingestion (files & folders)
- Metadata detection & preview (images, basic PDFs, docx)
- Metadata stripping (images included)
- Key-derivation (PBKDF2) and AES-256-GCM encryption
- Integrity verification (SHA-256)
- SQLite vault index + exportable JSON/PDF report
- CLI prototype 
- GUI planned (In-Progress)

## Tech stack
- Python 3.10+
- cryptography, Pillow, piexif, pikepdf / PyPDF2 (Planed)
- SQLite (built-in)
- pytest for tests

## Quickstart (CLI prototype)
1. Open New Terminal
2. Activate venv
3. Example - for ingest - python app.py ingest --path examples\sample.jpg --passphrase mypass
4. Restore - python app.py restore --id 2 --passphrase mypass --out restored_files
