import threading
import pathlib
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import traceback
import sys
import io

# Import your orchestrator (uses your project code)
from core.orchestrator import Orchestrator


class Redirector(io.TextIOBase):
    """Helper to capture prints and write them into a tkinter Text widget."""
    def __init__(self, write_fn):
        self.write_fn = write_fn

    def write(self, s):
        if s:
            self.write_fn(s)

    def flush(self):
        pass


class SecureVaultGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("SecureVault — GUI")
        self.pack(fill="both", expand=True)
        self.orch = Orchestrator()  # uses default db path (or your logic)

        self.selected_path: pathlib.Path | None = None
        self.preview_image = None  # keep reference to avoid GC
        self._build_ui()

    def _build_ui(self):
        # Top frame: file selection + preview
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="left", anchor="n")

        ttk.Button(btn_frame, text="Select File", command=self.select_file).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Select Folder", command=self.select_folder).pack(fill="x", pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=6)
        ttk.Button(btn_frame, text="Ingest (Encrypt & Store)", command=self.ingest_prompt).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Restore by ID", command=self.restore_prompt).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Open Reports Folder", command=self.open_reports).pack(fill="x", pady=2)

        # Preview area
        preview_frame = ttk.LabelFrame(top, text="Preview")
        preview_frame.pack(side="left", padx=8, pady=2, fill="both", expand=True)

        self.preview_label = ttk.Label(preview_frame, text="No file selected", anchor="center")
        self.preview_label.pack(fill="both", expand=True, padx=6, pady=6)

        # Bottom: status / console output
        out_frame = ttk.LabelFrame(self, text="Status / Output")
        out_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.text = tk.Text(out_frame, height=12, state="disabled", wrap="word")
        self.text.pack(fill="both", expand=True, padx=4, pady=4)

        # Redirect stdout/stderr into the text widget while GUI is open
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = Redirector(self._append_text)
        sys.stderr = Redirector(self._append_text)

    def _append_text(self, s: str):
        # Called in main thread only — but prints from worker threads will also call this.
        def _do():
            self.text.config(state="normal")
            self.text.insert("end", s)
            self.text.see("end")
            self.text.config(state="disabled")
        try:
            # schedule on main thread
            self.master.after(0, _do)
        except Exception:
            pass

    def select_file(self):
        file = filedialog.askopenfilename(title="Select file to ingest / preview")
        if not file:
            return
        self.selected_path = pathlib.Path(file)
        self._show_preview(self.selected_path)
        self._append_text(f"[GUI] Selected file: {self.selected_path}\n")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder to ingest recursively")
        if not folder:
            return
        self.selected_path = pathlib.Path(folder)
        self.preview_label.config(text=f"Folder selected:\n{self.selected_path}")
        self._append_text(f"[GUI] Selected folder: {self.selected_path}\n")

    def _show_preview(self, path: pathlib.Path):
        # Try to open as image; if fails show basic info
        try:
            img = Image.open(path)
            # generate thumbnail
            img.thumbnail((400, 300))
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.preview_image, text="")
        except Exception:
            self.preview_image = None
            self.preview_label.config(image="", text=f"Selected:\n{path.name}\n{path.stat().st_size} bytes")

    def ingest_prompt(self):
        if not self.selected_path:
            messagebox.showwarning("No selection", "Select a file or folder first.")
            return
        # ask passphrase masked
        passphrase = simpledialog.askstring("Passphrase", "Enter passphrase for encryption:", show="*")
        if passphrase is None:
            return
        # confirm
        if not messagebox.askyesno("Confirm", f"Ingest {self.selected_path}?"):
            return
        # run ingest in background thread
        t = threading.Thread(target=self._do_ingest, args=(str(self.selected_path), passphrase), daemon=True)
        t.start()

    def _do_ingest(self, path_str: str, passphrase: str):
        try:
            self._append_text(f"[GUI] Starting ingest for: {path_str}\n")
            # orchestrator expects path and passphrase (string or bytes)
            self.orch.ingest_path(path_str, passphrase)
            self._append_text(f"[GUI] Ingest finished for: {path_str}\n")
            messagebox.showinfo("Ingest finished", f"Ingest completed for:\n{path_str}\nCheck reports/ and DB for details.")
        except Exception as e:
            self._append_text(f"[GUI] Ingest error: {e}\n{traceback.format_exc()}\n")
            messagebox.showerror("Ingest error", f"Ingest failed:\n{e}")

    def restore_prompt(self):
        # ask for ID and passphrase and out folder
        rid = simpledialog.askinteger("Restore", "Enter record ID to restore (integer):")
        if rid is None:
            return
        passphrase = simpledialog.askstring("Passphrase", "Enter passphrase for decryption:", show="*")
        if passphrase is None:
            return
        out = filedialog.askdirectory(title="Select output folder for restored file")
        if not out:
            return
        # run restore in background
        t = threading.Thread(target=self._do_restore, args=(rid, passphrase, out), daemon=True)
        t.start()

    def _do_restore(self, rid: int, passphrase: str, out_folder: str):
        try:
            self._append_text(f"[GUI] Starting restore ID {rid} -> {out_folder}\n")
            self.orch.restore_id(rid, passphrase, out_folder)
            self._append_text(f"[GUI] Restore finished for ID {rid}\n")
            messagebox.showinfo("Restore finished", f"Record {rid} restored to:\n{out_folder}")
        except Exception as e:
            self._append_text(f"[GUI] Restore error: {e}\n{traceback.format_exc()}\n")
            messagebox.showerror("Restore error", f"Restore failed:\n{e}")

    def open_reports(self):
        # open reports folder in explorer (Windows)
        import os
        p = pathlib.Path("reports")
        if not p.exists():
            messagebox.showinfo("Reports", "No reports folder found.")
            return
        try:
            os.startfile(p.resolve())
        except Exception:
            messagebox.showinfo("Reports", f"Reports folder: {p.resolve()}")

    def on_close(self):
        # restore stdout/stderr
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        self.master.destroy()


def main():
    root = tk.Tk()
    # optional: set a minimum size
    root.minsize(700, 520)
    app = SecureVaultGUI(master=root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
