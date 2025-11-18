import json
from pathlib import Path
import base64

def _make_json_safe(obj):
    
    # bytes
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode("ascii")
    # pathlib.Path
    if isinstance(obj, Path):
        return str(obj)
    # dict
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    # list/tuple
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    # others (int, str, float, bool, None) - safe
    return obj

class ReportGenerator:
    def __init__(self):
        # Base directory = project root
        self.base_dir = Path(__file__).resolve().parent.parent
        self.reports_folder = self.base_dir / "reports"
        self.reports_folder.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, record_id, payload):
        safe_payload = _make_json_safe(payload)
        path = self.reports_folder / f"report_{record_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(safe_payload, f, indent=2)
        print("[+] Report generated:", path)
        return str(path)
