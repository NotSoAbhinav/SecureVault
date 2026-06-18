# Secure File Vault — Encryption & Metadata Removal

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](#license)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey.svg)](#usage)
[![Encryption](https://img.shields.io/badge/encryption-AES--256--GCM-green.svg)](#features)
[![Metadata Stripping](https://img.shields.io/badge/metadata-stripped-success.svg)](#features)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#running-tests)

A secure desktop tool that strips hidden metadata (EXIF, author, timestamps, etc.) from files, encrypts them using AES-256-GCM, stores them in a local vault, and generates tamper-evident JSON forensic reports.

## Features
- **Batch File Ingestion:** Process files individually or recursively scan entire directories.
- **Metadata Detection & Preview:** Inspect metadata fields for JPEG/PNG images, PDFs, and DOCX documents before encryption.
- **Comprehensive Metadata Stripping:** 
  * **Images (JPEG/PNG):** Purges all EXIF tags.
  * **PDFs:** Clears document info keys, XMP metadata streams, and document identifiers.
  * **DOCX:** Safely rewrites ZIP archive metadata files (`core.xml`, `app.xml`) to remove identifying information.
- **Strong Encryption:** Cryptographically derives keys using PBKDF2 (200,000 iterations of SHA-256) and encrypts payloads with AES-256-GCM.
- **Integrity Verification:** Uses SHA-256 hashes to guarantee data integrity before and after extraction.
- **SQLite Database Index:** Automatically records details, original paths, file hashes, and timestamps in a local SQLite index.
- **JSON Audit Reports:** Generates verification reports containing hashing audits and metadata history for every vault insertion.
- **Dual Interface:** Fully functional command-line prototype and Tkinter desktop GUI.

## Tech Stack
- **Python 3.10+**
- **cryptography** (AES-256-GCM encryption & PBKDF2 key derivation)
- **Pillow** & **piexif** (Image manipulation and EXIF stripping)
- **pikepdf** (PDF processing and metadata clearance)
- **sqlite3** (Local storage database engine)
- **pytest** (Test execution framework)

## Installation

1. Ensure Python 3.10+ is installed on your system.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 🖥️ Desktop GUI Prototype
Launch the graphical user interface to easily ingest/preview files, decrypt records, and browse reports:
```bash
python gui_app.py
```

### 💻 Command Line Interface (CLI)

#### Ingest a File or Folder
Cleans metadata, encrypts, and stores the file:
```bash
python app.py ingest --path examples/sample.JPG --passphrase mysecurepassphrase
```

#### Restore / Decrypt a File
Decrypts the vault record by its database ID and restores it to a target output folder:
```bash
python app.py restore --id 1 --passphrase mysecurepassphrase --out restored_files
```

### 🗃️ View Database Entries
Inspect the SQLite database records in a neat tabular grid:
```bash
python view_db.py
```

## Running Tests
Run the test suite using `pytest` to verify key derivation, metadata extraction, stripping algorithms, database persistence, and end-to-end integration:
```bash
python -m pytest tests/
```
