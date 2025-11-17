# Statement — Secure File Vault

**Problem statement:** Modern files often contain hidden metadata (EXIF, author, timestamps, GPS) that can leak user identity or sensitive context. Files stored unencrypted are vulnerable to theft or tampering.

**Scope:** Local vault for users to clean files, encrypt them, store them securely, and generate forensic reports. Supports images (JPEG/PNG), with extension to PDFs and DOCX.

**Target users:** Students, journalists, privacy-conscious users, digital forensic practitioners.

**High-level features:**
- Metadata detection & selective removal
- AES-256-GCM encryption with passphrase-derived keys
- SQLite metadata index and audit trail
- Restore/decrypt with integrity verification