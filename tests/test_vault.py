import os
import io
import pathlib
import zipfile
import sqlite3
import pytest
from PIL import Image
import piexif
import pikepdf

from core.crypto_engine import CryptoEngine
from core.analyzer import Analyzer
from core.cleaner import Cleaner
from core.storage_manager import StorageManager
from core.orchestrator import Orchestrator
from core.utils import user_data_dir

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture
def sample_image(temp_dir):
    img_path = temp_dir / "test_image.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    
    # Add EXIF metadata
    zeroth_ifd = {piexif.ImageIFD.Make: u"TestCamera", piexif.ImageIFD.Model: u"M1"}
    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)
    
    img.save(img_path, "jpeg", exif=exif_bytes)
    return img_path

@pytest.fixture
def sample_pdf(temp_dir):
    pdf_path = temp_dir / "test_doc.pdf"
    # Create simple PDF using pikepdf
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()
    with pdf.open_metadata() as meta:
        meta["dc:title"] = "Test Title"
        meta["dc:creator"] = ["Test Author"]
    pdf.docinfo["/Author"] = "Test Author"
    pdf.docinfo["/Title"] = "Test Title"
    pdf.save(pdf_path)
    return pdf_path

@pytest.fixture
def sample_docx(temp_dir):
    docx_path = temp_dir / "test_doc.docx"
    # Create a minimal ZIP file mimicking docx structure
    with zipfile.ZipFile(docx_path, "w") as z:
        core_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:creator>Test Creator</dc:creator>'
            '<dc:title>Test Title</dc:title>'
            '</cp:coreProperties>'
        )
        app_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Company>Test Company</Company>'
            '</Properties>'
        )
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)
        z.writestr("word/document.xml", "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>Hello World</w:t></w:r></w:p></w:body></w:document>")
    return docx_path

def test_crypto_engine():
    engine = CryptoEngine(iterations=1000) # use small iterations for faster tests
    password = b"secret_pass"
    plaintext = b"sensitive metadata-free content"
    
    salt, nonce, ct = engine.encrypt_bytes(plaintext, password)
    assert len(salt) == 16
    assert len(nonce) == 12
    
    decrypted = engine.decrypt_bytes(ct, password, salt, nonce)
    assert decrypted == plaintext

def test_metadata_extraction_image(sample_image):
    analyzer = Analyzer()
    meta = analyzer.extract_metadata(sample_image)
    assert any("Image_" in k for k in meta.keys())

def test_metadata_extraction_pdf(sample_pdf):
    analyzer = Analyzer()
    meta = analyzer.extract_metadata(sample_pdf)
    assert meta.get("PDF_info:/Author") == "Test Author"
    assert meta.get("PDF_info:/Title") == "Test Title"
    assert any("PDF_xmp:" in k for k in meta.keys())

def test_metadata_extraction_docx(sample_docx):
    analyzer = Analyzer()
    meta = analyzer.extract_metadata(sample_docx)
    assert meta.get("DOCX_core:creator") == "Test Creator"
    assert meta.get("DOCX_core:title") == "Test Title"
    assert meta.get("DOCX_app:Company") == "Test Company"

def test_metadata_cleaning_image(sample_image):
    cleaner = Cleaner()
    analyzer = Analyzer()
    
    # check that metadata exists originally
    orig_meta = analyzer.extract_metadata(sample_image)
    assert orig_meta != {}
    
    cleaned_bytes = cleaner.remove_metadata_bytes(sample_image, orig_meta)
    
    # write cleaned bytes to temp file and parse again
    cleaned_file = sample_image.parent / "cleaned_img.jpg"
    with open(cleaned_file, "wb") as f:
        f.write(cleaned_bytes)
        
    new_meta = analyzer.extract_metadata(cleaned_file)
    assert new_meta == {}

def test_metadata_cleaning_pdf(sample_pdf):
    cleaner = Cleaner()
    analyzer = Analyzer()
    
    orig_meta = analyzer.extract_metadata(sample_pdf)
    assert "PDF_info:/Author" in orig_meta
    
    cleaned_bytes = cleaner.remove_metadata_bytes(sample_pdf, orig_meta)
    
    cleaned_file = sample_pdf.parent / "cleaned_doc.pdf"
    with open(cleaned_file, "wb") as f:
        f.write(cleaned_bytes)
        
    new_meta = analyzer.extract_metadata(cleaned_file)
    assert "PDF_info:/Author" not in new_meta
    assert "PDF_xmp:dc:creator" not in new_meta

def test_metadata_cleaning_docx(sample_docx):
    cleaner = Cleaner()
    analyzer = Analyzer()
    
    orig_meta = analyzer.extract_metadata(sample_docx)
    assert orig_meta.get("DOCX_core:creator") == "Test Creator"
    
    cleaned_bytes = cleaner.remove_metadata_bytes(sample_docx, orig_meta)
    
    cleaned_file = sample_docx.parent / "cleaned_doc.docx"
    with open(cleaned_file, "wb") as f:
        f.write(cleaned_bytes)
        
    new_meta = analyzer.extract_metadata(cleaned_file)
    assert new_meta.get("DOCX_core:creator") is None
    assert new_meta.get("DOCX_app:Company") is None

def test_storage_manager(temp_dir):
    db_file = temp_dir / "test_vault.db"
    manager = StorageManager(str(db_file.resolve()))
    
    # Insert record
    rec_id = manager.insert_record(
        original_name="test.jpg",
        original_path="/path/to/test.jpg",
        encrypted_name="test.jpg.vault",
        salt=b"salt1234salt1234",
        nonce=b"nonce1234567",
        original_sha256="abc",
        cleaned_sha256="def",
        encrypted_sha256="ghi",
        timestamp="2025-11-17T18:08:20Z"
    )
    
    assert rec_id is not None
    
    # Retrieve record
    rec = manager.get_record(rec_id)
    assert rec is not None
    assert rec["original_name"] == "test.jpg"
    assert rec["salt"] == b"salt1234salt1234"
    assert rec["nonce"] == b"nonce1234567"

def test_orchestrator_end_to_end(temp_dir, sample_pdf):
    # Set up test database path
    test_db = temp_dir / "test_orchestrator.db"
    orch = Orchestrator(db_path=str(test_db.resolve()))
    
    # override iterations for test speed
    orch.crypto.iterations = 1000
    
    # Ingest
    passphrase = "my_secure_passphrase"
    orch.ingest_path(sample_pdf, passphrase)
    
    # Check that record was added
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM vault_files WHERE original_name = ?", (sample_pdf.name,))
    row = c.fetchone()
    assert row is not None
    record_id = row["id"]
    conn.close()
    
    # Restore
    restored_folder = temp_dir / "restored"
    orch.restore_id(record_id, passphrase, restored_folder)
    
    restored_file = restored_folder / sample_pdf.name
    assert restored_file.exists()
    
    # Ensure it's a valid PDF (can be opened)
    with pikepdf.Pdf.open(restored_file) as restored_pdf:
        assert len(restored_pdf.pages) == 1
