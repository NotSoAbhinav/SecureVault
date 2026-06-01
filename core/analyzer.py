import hashlib
from PIL import Image
import piexif
import os
class Analyzer:
    def hash_file(self,path, chunk_size=8192):
        h=hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda:f.read(chunk_size),b""):
                h.update(chunk)
            return h.hexdigest()
    def hash_bytes(self,b):
        h=hashlib.sha256()
        h.update(b)
        return h.hexdigest()
    def extract_metadata(self, path):
        try:
            with open(path, "rb") as f:
                sig = f.read(8)
            
            # Check signatures
            if sig.startswith(b"%PDF"):
                import pikepdf
                metadata = {}
                with pikepdf.Pdf.open(path) as pdf:
                    for key, val in pdf.docinfo.items():
                        metadata[f"PDF_info:{str(key)}"] = str(val)
                    try:
                        meta = pdf.open_metadata()
                        for k, v in meta.items():
                            metadata[f"PDF_xmp:{str(k)}"] = str(v)
                    except Exception:
                        pass
                return metadata

            elif sig.startswith(b"PK\x03\x04"):
                import zipfile
                import xml.etree.ElementTree as ET
                if not zipfile.is_zipfile(path):
                    return {}
                metadata = {}
                with zipfile.ZipFile(path) as z:
                    if "docProps/core.xml" in z.namelist():
                        data = z.read("docProps/core.xml")
                        root = ET.fromstring(data)
                        for elem in root.iter():
                            name = elem.tag.split("}")[-1]
                            if elem.text:
                                metadata[f"DOCX_core:{name}"] = elem.text
                    if "docProps/app.xml" in z.namelist():
                        data = z.read("docProps/app.xml")
                        root = ET.fromstring(data)
                        for elem in root.iter():
                            name = elem.tag.split("}")[-1]
                            if elem.text and name in ["Application", "Company", "Template"]:
                                metadata[f"DOCX_app:{name}"] = elem.text
                return metadata

            else:
                # Try image
                img = Image.open(path)
                exif_dict = piexif.load(img.info.get("exif", b""))
                metadata = {}
                for ifd in exif_dict:
                    if exif_dict[ifd]:
                        metadata[f"Image_{ifd}"] = list(exif_dict[ifd].keys())
                return metadata
        except Exception:
            return {}