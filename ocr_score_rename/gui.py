from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import fitz

from ocr_score_rename.config import load_app_settings, load_instruments, load_settings, save_settings
from ocr_score_rename.config_dialog import InstrumentsConfigDialog
from ocr_score_rename.instruments import Instrument
from ocr_score_rename.naming import FORMAT_PRESETS, NamingSettings, VoiceParts, build_output_name
from ocr_score_rename.ocr import render_page_image
from ocr_score_rename.rename import list_pdfs_in_directory, process_directory
from ocr_score_rename.page_regions import extract_header_text_from_page
from ocr_score_rename.title import extract_work_title_from_header


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OCR Score Rename")
        self.minsize(620, 580)

        self.instruments: list[Instrument] = load_instruments()
        self.naming_settings = load_settings()
        app_settings = load_app_settings()

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar(value=app_settings.get("output_dir", ""))
        self.score_title = tk.StringVar()
        self.separator = tk.StringVar(value=self.naming_settings.separator)
        self.format_preset = tk.StringVar(value=self.naming_settings.preset)
        self.include_tuning = tk.BooleanVar(value=self.naming_settings.include_tuning_when_known)
        self.use_separate_output = tk.BooleanVar(value=app_settings.get("use_separate_output", False))
        self.auto_detect_title = tk.BooleanVar(value=app_settings.get("auto_detect_title", True))
        self.status = tk.StringVar(value="Eingabeordner wählen, um zu starten.")
        self.preview = tk.StringVar()

        self._build_ui()
        self._toggle_output_dir()
        self._toggle_title_entry()
        self._update_preview()
        if len(self.instruments) < 20:
            self.status.set(
                "Hinweis: Instrumentenliste wirkt veraltet — unter „Instrumente…“ "
                "„Standard wiederherstellen“ wählen."
            )

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 5}
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Checkbutton(
            frame,
            text="Titel automatisch erkennen (groß, links oben)",
            variable=self.auto_detect_title,
            command=self._on_auto_title_toggled,
        ).grid(row=0, column=1, sticky=tk.W, **padding)

        ttk.Label(frame, text="Werktitel").grid(row=1, column=0, sticky=tk.W, **padding)
        self.title_entry = ttk.Entry(frame, textvariable=self.score_title, width=52)
        self.title_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, **padding)

        ttk.Label(frame, text="Eingabeordner").grid(row=2, column=0, sticky=tk.W, **padding)
        ttk.Entry(frame, textvariable=self.input_dir, width=52).grid(
            row=2, column=1, sticky=tk.EW, **padding
        )
        ttk.Button(frame, text="Durchsuchen…", command=self._pick_input_dir).grid(row=2, column=2, **padding)

        ttk.Checkbutton(
            frame,
            text="Anderen Zielordner verwenden",
            variable=self.use_separate_output,
            command=self._toggle_output_dir,
        ).grid(row=3, column=1, sticky=tk.W, **padding)

        ttk.Label(frame, text="Zielordner").grid(row=4, column=0, sticky=tk.W, **padding)
        self.output_entry = ttk.Entry(frame, textvariable=self.output_dir, width=52)
        self.output_entry.grid(row=4, column=1, sticky=tk.EW, **padding)
        self.output_button = ttk.Button(frame, text="Durchsuchen…", command=self._pick_output_dir)
        self.output_button.grid(row=4, column=2, **padding)

        format_box = ttk.LabelFrame(frame, text="Dateibenennung", padding=8)
        format_box.grid(row=5, column=0, columnspan=3, sticky=tk.EW, **padding)

        ttk.Label(format_box, text="Reihenfolge").grid(row=0, column=0, sticky=tk.W, pady=2)
        preset_combo = ttk.Combobox(
            format_box,
            textvariable=self.format_preset,
            values=list(FORMAT_PRESETS),
            state="readonly",
            width=28,
        )
        preset_combo.grid(row=0, column=1, sticky=tk.W, padx=(6, 0), pady=2)
        preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_preview())

        ttk.Label(format_box, text="Trennzeichen").grid(row=1, column=0, sticky=tk.W, pady=2)
        sep_entry = ttk.Entry(format_box, textvariable=self.separator, width=8)
        sep_entry.grid(row=1, column=1, sticky=tk.W, padx=(6, 0), pady=2)
        sep_entry.bind("<KeyRelease>", lambda _event: self._update_preview())

        ttk.Checkbutton(
            format_box,
            text="Stimmung im Dateinamen (wenn bekannt)",
            variable=self.include_tuning,
            command=self._update_preview,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(format_box, textvariable=self.preview).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        ttk.Label(frame, text="PDFs im Ordner").grid(row=6, column=0, sticky=tk.NW, **padding)
        self.file_list = tk.Listbox(frame, height=8, selectmode=tk.EXTENDED)
        self.file_list.grid(row=6, column=1, columnspan=2, sticky=tk.NSEW, **padding)

        button_row = ttk.Frame(frame)
        button_row.grid(row=7, column=1, columnspan=2, sticky=tk.EW, **padding)
        ttk.Button(button_row, text="Instrumente…", command=self._open_config).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Umbenennen", command=self._run).pack(side=tk.RIGHT)

        ttk.Label(frame, textvariable=self.status).grid(row=8, column=0, columnspan=3, sticky=tk.W, **padding)

        self.log = scrolledtext.ScrolledText(frame, height=8, state=tk.DISABLED)
        self.log.grid(row=9, column=0, columnspan=3, sticky=tk.NSEW, **padding)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)
        frame.rowconfigure(9, weight=1)

    def _toggle_title_entry(self) -> None:
        state = tk.DISABLED if self.auto_detect_title.get() else tk.NORMAL
        self.title_entry.configure(state=state)

    def _on_auto_title_toggled(self) -> None:
        self._toggle_title_entry()
        if self.auto_detect_title.get():
            self._preview_title_from_folder()

    def _current_naming_settings(self) -> NamingSettings:
        preset = self.format_preset.get()
        return NamingSettings(
            separator=self.separator.get(),
            parts_order=FORMAT_PRESETS.get(preset, self.naming_settings.parts_order),
            include_tuning_when_known=self.include_tuning.get(),
            preset=preset,
        )

    def _update_preview(self) -> None:
        naming = self._current_naming_settings()
        example = build_output_name(
            VoiceParts(
                instrument="Bariton",
                tuning="B",
                clef="VSl",
                number=1,
                title=self.score_title.get().strip() or "Marsch der Freiwilligen",
            ),
            settings=naming,
            extension=".pdf",
        )
        self.preview.set(f"Vorschau: {example}")

    def _toggle_output_dir(self) -> None:
        enabled = self.use_separate_output.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.output_entry.configure(state=state)
        self.output_button.configure(state=state)

    def _open_config(self) -> None:
        InstrumentsConfigDialog(self, self.instruments, on_save=self._on_instruments_saved)

    def _on_instruments_saved(self, instruments: list[Instrument]) -> None:
        self.instruments = instruments
        self.status.set(f"{len(self.instruments)} Instrumente geladen.")

    def _pick_input_dir(self) -> None:
        path = filedialog.askdirectory()
        if not path:
            return
        self.input_dir.set(path)
        self._refresh_pdf_list()

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _preview_title_from_folder(self) -> None:
        directory = Path(self.input_dir.get().strip()) if self.input_dir.get().strip() else None
        if directory is None or not directory.is_dir():
            return

        pdfs = list_pdfs_in_directory(directory)
        if not pdfs:
            return

        def detect() -> None:
            try:
                with fitz.open(pdfs[0]) as doc:
                    page = doc.load_page(0)
                    image = render_page_image(page)
                    header = extract_header_text_from_page(page, image)
                    title = extract_work_title_from_header(header, instruments=self.instruments) or ""
            except Exception:
                title = ""

            def apply() -> None:
                if self.auto_detect_title.get():
                    self.score_title.set(title)
                    self._update_preview()
                    if title:
                        self.status.set(f"Titel erkannt: „{title}“")
                    else:
                        self.status.set("Titel konnte nicht erkannt werden.")

            self.after(0, apply)

        threading.Thread(target=detect, daemon=True).start()

    def _refresh_pdf_list(self) -> None:
        self.file_list.delete(0, tk.END)
        directory = Path(self.input_dir.get().strip()) if self.input_dir.get().strip() else None
        if directory is None or not directory.is_dir():
            self.status.set("Kein gültiger Eingabeordner.")
            return

        pdfs = list_pdfs_in_directory(directory)
        for pdf in pdfs:
            self.file_list.insert(tk.END, pdf.name)
        self.status.set(f"{len(pdfs)} PDF(s) in „{directory.name}“ gefunden.")
        if self.auto_detect_title.get():
            self._preview_title_from_folder()
        else:
            self._update_preview()

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _run(self) -> None:
        input_path = self.input_dir.get().strip()
        if not input_path:
            messagebox.showwarning("Ordner fehlt", "Bitte einen Eingabeordner wählen.")
            return
        if not self.auto_detect_title.get() and not self.score_title.get().strip():
            messagebox.showwarning("Titel fehlt", "Bitte einen Werktitel eingeben oder automatische Erkennung aktivieren.")
            return

        input_directory = Path(input_path)
        if not input_directory.is_dir():
            messagebox.showwarning("Ungültiger Ordner", "Der Eingabeordner existiert nicht.")
            return

        output_directory: Path | None = None
        if self.use_separate_output.get():
            output_value = self.output_dir.get().strip()
            if not output_value:
                messagebox.showwarning("Zielordner fehlt", "Bitte einen Zielordner wählen.")
                return
            output_directory = Path(output_value)

        naming = self._current_naming_settings()
        save_settings(
            naming,
            use_separate_output=self.use_separate_output.get(),
            output_dir=self.output_dir.get().strip(),
            auto_detect_title=self.auto_detect_title.get(),
        )
        self.naming_settings = naming

        manual_title = self.score_title.get().strip() or None
        threading.Thread(
            target=self._process,
            args=(input_directory, output_directory, naming, manual_title, self.auto_detect_title.get()),
            daemon=True,
        ).start()

    def _process(
        self,
        input_directory: Path,
        output_directory: Path | None,
        naming: NamingSettings,
        manual_title: str | None,
        auto_detect_title: bool,
    ) -> None:
        self.status.set("Verarbeitung läuft…")
        try:
            results = process_directory(
                input_directory,
                manual_title,
                output_dir=output_directory,
                instruments=self.instruments,
                naming=naming,
                auto_detect_title=auto_detect_title,
            )
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: messagebox.showerror("Fehler", str(exc)))
            self.after(0, lambda: self.status.set("Fehlgeschlagen."))
            return

        def report() -> None:
            self.log.configure(state=tk.NORMAL)
            self.log.delete("1.0", tk.END)
            self.log.configure(state=tk.DISABLED)
            for result in results:
                label = result.instrument or "unbekannt"
                self._append_log(
                    f"{result.source.name} → {result.destination.name} ({label}, „{result.title}“)"
                )
            self._refresh_pdf_list()
            mode = "umbenannt" if output_directory is None else "kopiert"
            self.status.set(f"Fertig. {len(results)} Datei(en) {mode}.")

        self.after(0, report)


def main() -> None:
    app = App()
    app.mainloop()
