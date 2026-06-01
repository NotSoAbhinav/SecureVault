from PIL import Image
import piexif
import io

class Cleaner:
    def remove_metadata_bytes(self, path, metadata):
        try:
            with open(path, "rb") as f:
                sig = f.read(8)

            if sig.startswith(b"%PDF"):
                import pikepdf
                out_bytes = io.BytesIO()
                with pikepdf.Pdf.open(path) as pdf:
                    if hasattr(pdf, "docinfo"):
                        for key in list(pdf.docinfo.keys()):
                            del pdf.docinfo[key]
                    try:
                        del pdf.Root.Metadata
                    except Exception:
                        pass
                    try:
                        del pdf.Root.ID
                    except Exception:
                        pass
                    pdf.save(out_bytes)
                return out_bytes.getvalue()

            elif sig.startswith(b"PK\x03\x04"):
                import zipfile
                out_zip_data = io.BytesIO()
                with zipfile.ZipFile(path, "r") as z_in:
                    with zipfile.ZipFile(out_zip_data, "w", zipfile.ZIP_DEFLATED) as z_out:
                        for item in z_in.infolist():
                            content = z_in.read(item.filename)
                            if item.filename == "docProps/core.xml":
                                minimal_core = (
                                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                                    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                                    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                                    'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                                    '</cp:coreProperties>'
                                )
                                z_out.writestr(item.filename, minimal_core.encode("utf-8"))
                            elif item.filename == "docProps/app.xml":
                                minimal_app = (
                                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                                    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
                                    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
                                    '</Properties>'
                                )
                                z_out.writestr(item.filename, minimal_app.encode("utf-8"))
                            else:
                                z_out.writestr(item, content)
                return out_zip_data.getvalue()

            else:
                # Images / Default Pillow flow
                img = Image.open(path)
                data = io.BytesIO()
                img.save(data, format=img.format)  # saving without exif strips metadata
                return data.getvalue()
        except Exception:
            # fallback: return original bytes (no cleaning done)
            with open(path, "rb") as f:
                return f.read()
