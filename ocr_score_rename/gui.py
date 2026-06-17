from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ocr_score_rename.config import load_instruments
from ocr_score_rename.config_dialog import InstrumentsConfigDialog
from ocr_score_rename.instruments import Instrument
from ocr_score_rename.rename import process_pdfs


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OCR Score Rename")
        self.minsize(520, 420)

        self.pdf_paths: list[Path] = []
        self.instruments: list[Instrument] = load_instruments()
        self.output_dir = tk.StringVar()
        self.score_title = tk.StringVar()
        self.status = tk.StringVar(value="PDF-Scans auswählen, um zu starten.")

        self._build_ui()

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Werktitel").grid(row=0, column=0, sticky=tk.W, **padding)
        ttk.Entry(frame, textvariable=self.score_title, width=50).grid(
            row=0, column=1, columnspan=2, sticky=tk.EW, **padding
        )

        ttk.Label(frame, text="Zielordner").grid(row=1, column=0, sticky=tk.W, **padding)
        ttk.Entry(frame, textvariable=self.output_dir, width=50).grid(
            row=1, column=1, sticky=tk.EW, **padding
        )
        ttk.Button(frame, text="Durchsuchen…", command=self._pick_output_dir).grid(
            row=1, column=2, **padding
        )

        ttk.Label(frame, text="PDF-Scans").grid(row=2, column=0, sticky=tk.NW, **padding)
        self.file_list = tk.Listbox(frame, height=8, selectmode=tk.EXTENDED)
        self.file_list.grid(row=2, column=1, columnspan=2, sticky=tk.NSEW, **padding)

        button_row = ttk.Frame(frame)
        button_row.grid(row=3, column=1, columnspan=2, sticky=tk.EW, **padding)
        ttk.Button(button_row, text="PDFs hinzufügen…", command=self._add_pdfs).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="Auswahl entfernen", command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="Instrumente…", command=self._open_config).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Umbenennen & kopieren", command=self._run).pack(side=tk.RIGHT)

        ttk.Label(frame, textvariable=self.status).grid(
            row=4, column=0, columnspan=3, sticky=tk.W, **padding
        )

        self.log = scrolledtext.ScrolledText(frame, height=10, state=tk.DISABLED)
        self.log.grid(row=5, column=0, columnspan=3, sticky=tk.NSEW, **padding)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.rowconfigure(5, weight=1)

    def _open_config(self) -> None:
        InstrumentsConfigDialog(self, self.instruments, on_save=self._on_instruments_saved)

    def _on_instruments_saved(self, instruments: list[Instrument]) -> None:
        self.instruments = instruments
        self.status.set(f"{len(self.instruments)} Instrumente geladen.")

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _add_pdfs(self) -> None:
        paths = filedialog.askopenfilenames(
            title="PDF-Scans auswählen",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")],
        )
        for path in paths:
            pdf = Path(path)
            if pdf not in self.pdf_paths:
                self.pdf_paths.append(pdf)
                self.file_list.insert(tk.END, pdf.name)
        self.status.set(f"{len(self.pdf_paths)} Datei(en) ausgewählt.")

    def _remove_selected(self) -> None:
        selected = list(self.file_list.curselection())
        for index in reversed(selected):
            self.file_list.delete(index)
            del self.pdf_paths[index]
        self.status.set(f"{len(self.pdf_paths)} Datei(en) ausgewählt.")

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _run(self) -> None:
        if not self.pdf_paths:
            messagebox.showwarning("Keine Dateien", "Mindestens einen PDF-Scan hinzufügen.")
            return
        if not self.score_title.get().strip():
            messagebox.showwarning("Titel fehlt", "Bitte einen Werktitel eingeben.")
            return
        if not self.output_dir.get().strip():
            messagebox.showwarning("Ordner fehlt", "Bitte einen Zielordner wählen.")
            return

        threading.Thread(target=self._process, daemon=True).start()

    def _process(self) -> None:
        self.status.set("Verarbeitung läuft…")
        try:
            results = process_pdfs(
                pdf_paths=list(self.pdf_paths),
                output_dir=Path(self.output_dir.get()),
                score_title=self.score_title.get().strip(),
                instruments=self.instruments,
            )
        except Exception as exc:  # noqa: BLE001 — show any failure in the GUI
            self.after(0, lambda: messagebox.showerror("Fehler", str(exc)))
            self.after(0, lambda: self.status.set("Fehlgeschlagen."))
            return

        def report() -> None:
            self.log.configure(state=tk.NORMAL)
            self.log.delete("1.0", tk.END)
            self.log.configure(state=tk.DISABLED)
            for result in results:
                label = result.instrument or "unbekannt"
                self._append_log(f"{result.source.name} → {result.destination.name} ({label})")
            self.status.set(f"Fertig. {len(results)} Datei(en) kopiert.")

        self.after(0, report)


def main() -> None:
    app = App()
    app.mainloop()
