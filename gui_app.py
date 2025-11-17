# gui_db_viewer.py
import sys
import csv
import json
import sqlite3
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter
)
from PySide6.QtCore import Qt
from core.orchestrator import Orchestrator
from core.storage_manager import StorageManager

PROJECT_ROOT = Path(__file__).resolve().parent

class DBViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure File Vault — DB Viewer")
        self.setMinimumSize(900, 560)

        self.orch = Orchestrator()               # re-uses existing orchestrator
        self.storage = self.orch.storage         # access storage manager for db path

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Top control row
        row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Table")
        self.btn_refresh.clicked.connect(self.load_table)
        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.clicked.connect(self.export_csv)
        self.btn_export_report = QPushButton("Export Selected Report JSON")
        self.btn_export_report.clicked.connect(self.export_selected_report)
        self.btn_restore = QPushButton("Restore Selected")
        self.btn_restore.clicked.connect(self.restore_selected)
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_selected)

        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_export_csv)
        row.addWidget(self.btn_export_report)
        row.addWidget(self.btn_restore)
        row.addWidget(self.btn_delete)
        row.addStretch()
        layout.addLayout(row)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Original Name", "Encrypted Name", "Original SHA256",
            "Cleaned SHA256", "Timestamp"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        layout.addWidget(self.table, 8)

        # Details + Console
        bottom = QHBoxLayout()
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        bottom.addWidget(self.details, 2)

        right_col = QVBoxLayout()
        self.lbl_dbpath = QLabel(f"DB: {str(self.storage.db_path)}")
        right_col.addWidget(self.lbl_dbpath)
        self.btn_open_db = QPushButton("Open DB in DB Browser (if installed)")
        self.btn_open_db.clicked.connect(self.open_in_db_browser)
        right_col.addWidget(self.btn_open_db)
        right_col.addStretch()
        bottom.addLayout(right_col, 1)

        layout.addLayout(bottom, 3)

        # connect table selection
        self.table.itemSelectionChanged.connect(self.on_selection_change)

        # initial load
        self.load_table()

    def _connect(self):
        return sqlite3.connect(str(self.storage.db_path))

    def load_table(self):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT id, original_name, encrypted_name, original_sha256, cleaned_sha256, timestamp FROM vault_files ORDER BY id DESC")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Failed to read DB: {e}")
            return

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(r, c, item)

        self.details.clear()
        self.append_log(f"Loaded {len(rows)} records.")

    def append_log(self, text):
        self.details.append(text)

    def on_selection_change(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        record_id = int(self.table.item(row, 0).text())
        self.show_record_details(record_id)

    def show_record_details(self, record_id):
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM vault_files WHERE id = ?", (record_id,))
        rec = cur.fetchone()
        conn.close()
        if not rec:
            self.details.setPlainText("Record not found.")
            return
        out = []
        for k in rec.keys():
            v = rec[k]
            # convert bytes to base64 display if needed
            if isinstance(v, (bytes, bytearray)):
                import base64
                v = f"<bytes, base64: {base64.b64encode(v).decode()[:32]}...>"
            out.append(f"{k}: {v}")
        self.details.setPlainText("\n".join(out))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", str(PROJECT_ROOT / "vault_export.csv"), "CSV files (*.csv)")
        if not path:
            return
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT * FROM vault_files")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            conn.close()

            with open(path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for row in rows:
                    # convert bytes to base64 for CSV
                    newrow = []
                    for v in row:
                        if isinstance(v, (bytes, bytearray)):
                            import base64
                            newrow.append(base64.b64encode(v).decode("ascii"))
                        else:
                            newrow.append(v)
                    writer.writerow(newrow)
            QMessageBox.information(self, "Exported", f"CSV exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def export_selected_report(self):
        sel = self.table.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Select", "Select a row to export its JSON report.")
            return
        row = sel[0].row()
        record_id = int(self.table.item(row, 0).text())
        # fetch fields from DB and prepare JSON
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM vault_files WHERE id = ?", (record_id,))
        rec = cur.fetchone()
        conn.close()
        if not rec:
            QMessageBox.warning(self, "Not found", "Record not found.")
            return
        payload = {}
        for k in rec.keys():
            v = rec[k]
            if isinstance(v, (bytes, bytearray)):
                import base64
                v = base64.b64encode(v).decode("ascii")
            payload[k] = v

        path, _ = QFileDialog.getSaveFileName(self, "Save report JSON", str(PROJECT_ROOT / f"export_report_{record_id}.json"), "JSON files (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        QMessageBox.information(self, "Saved", f"Report exported: {path}")

    def restore_selected(self):
        sel = self.table.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Select", "Select a row to restore.")
            return
        row = sel[0].row()
        record_id = int(self.table.item(row, 0).text())
        out = QFileDialog.getExistingDirectory(self, "Choose restore folder", str(PROJECT_ROOT))
        if not out:
            return
        # ask for passphrase
        passphrase, ok = QInputDialog.getText(self, "Passphrase", "Enter passphrase:", QLineEdit.Password)
        if not ok:
            return
        try:
            self.orch.restore_id(record_id, passphrase, out)
            QMessageBox.information(self, "Restored", f"Record {record_id} restored to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Restore failed", str(e))

    def delete_selected(self):
        sel = self.table.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Select", "Select a row to delete.")
            return
        row = sel[0].row()
        record_id = int(self.table.item(row, 0).text())
        confirm = QMessageBox.question(self, "Delete", f"Delete record {record_id}? This will remove DB entry and encrypted file (yes/no).", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        try:
            # fetch encrypted filename, delete file
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT encrypted_name FROM vault_files WHERE id = ?", (record_id,))
            res = cur.fetchone()
            if res:
                enc_name = res[0]
                enc_path = (PROJECT_ROOT / "vault_store" / enc_name)
                if enc_path.exists():
                    enc_path.unlink()
            # delete DB record
            cur.execute("DELETE FROM vault_files WHERE id = ?", (record_id,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Deleted", f"Record {record_id} deleted.")
            self.load_table()
        except Exception as e:
            QMessageBox.critical(self, "Delete failed", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DBViewer()
    w.show()
    sys.exit(app.exec())
