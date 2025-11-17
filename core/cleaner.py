from PIL import Image
import piexif
import io

class Cleaner:
    def remove_metadata_bytes(self, path, metadata):
        # For images: remove EXIF by re-saving without exif
        try:
            img = Image.open(path)
            data = io.BytesIO()
            img.save(data, format=img.format)  # saving without exif strips metadata
            return data.getvalue()
        except Exception:
            # fallback: return original bytes (no cleaning done)
            with open(path, "rb") as f:
                return f.read()
