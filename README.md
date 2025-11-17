# Secure File Vault — Encryption & Metadata Removal

**Short:** A Secure desktop tool that strips hidden metadata from files, encrypts them (AES-256-GCM), stores them in a local vault and generates tamper-evident forensic reports.

## Features
- Batch file ingestion (files & folders)
- Metadata detection & preview (images, basic PDFs, docx)
- Metadata stripping (images included)
- Key-derivation (PBKDF2) and AES-256-GCM encryption
- Integrity verification (SHA-256)
- SQLite vault index + exportable JSON/PDF report
- CLI prototype — GUI planned

## Tech stack
- Python 3.10+
- cryptography, Pillow, piexif, pikepdf / PyPDF2 (optional)
- SQLite (built-in)
- pytest for tests

## Quickstart (CLI prototype)
1. Create virtualenv:
```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\\Scripts\\activate
pip install -r requirements.txt