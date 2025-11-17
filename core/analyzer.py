import hashlib
from PIL import Image
import piexif
import os
class Analyzer:
    def hash_file(self,path chunk_size=8192):
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
            img = Image.open(path)
            exif_dict = piexif.load(img.info.get("exif", b""))
            metadata = {}
            for ifd in exif_dict:
                if exif_dict[ifd]:
                    metadata[ifd] = list(exif_dict[ifd].keys())
            return metadata
        except Exception:
            return {}