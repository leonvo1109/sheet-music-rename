from __future__ import annotations

import copy
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from ocr_score_rename.config import load_default_instruments, save_instruments
from ocr_score_rename.instruments import Instrument
from ocr_score_rename.synonym_validation import validate_synonym
from ocr_score_rename.text_normalize import normalized_key


class InstrumentsConfigDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, instruments: list[Instrument], on_save: Callable[[list[Instrument]], None]) -> None:
        super().__init__(parent)
        self.title("Instrumente konfigurieren")
        self.transient(parent)
        self.grab_set()
        self.minsize(600, 460)

        self._on_save = on_save
        self._instruments = copy.deepcopy(instruments)
        self._selected_index: int | None = None

        self.name_var = tk.StringVar()
        self.tuning_var = tk.StringVar()
        self.synonym_var = tk.StringVar()
        self._name_trace = self.name_var.trace_add("write", lambda *_: self._sync_name())
        self._tuning_trace = self.tuning_var.trace_add("write", lambda *_: self._sync_tuning())

        self._build_ui()
        if self._instruments:
            self.instrument_list.selection_set(0)
            self._select_instrument(0)
        else:
            self._clear_detail()

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _format_list_label(self, instrument: Instrument) -> str:
        if instrument.tuning:
            return f"{instrument.name} ({instrument.tuning})"
        return instrument.name

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Instrumente").grid(row=0, column=0, sticky=tk.W, **padding)
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, rowspan=5, sticky=tk.NSEW, **padding)

        self.instrument_list = tk.Listbox(list_frame, width=24, height=14, exportselection=False)
        self.instrument_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.instrument_list.bind("<<ListboxSelect>>", self._on_list_select)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.instrument_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.instrument_list.configure(yscrollcommand=scrollbar.set)

        list_buttons = ttk.Frame(frame)
        list_buttons.grid(row=6, column=0, sticky=tk.EW, **padding)
        ttk.Button(list_buttons, text="Neu", command=self._add_instrument).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(list_buttons, text="Löschen", command=self._remove_instrument).pack(side=tk.LEFT)

        ttk.Label(frame, text="Name").grid(row=0, column=1, sticky=tk.W, **padding)
        self.name_entry = ttk.Entry(frame, textvariable=self.name_var, width=36)
        self.name_entry.grid(row=1, column=1, sticky=tk.EW, **padding)

        ttk.Label(frame, text="Standard-Stimmung").grid(row=2, column=1, sticky=tk.W, **padding)
        tuning_row = ttk.Frame(frame)
        tuning_row.grid(row=3, column=1, sticky=tk.EW, **padding)
        ttk.Entry(tuning_row, textvariable=self.tuning_var, width=10).pack(side=tk.LEFT)
        ttk.Label(
            tuning_row,
            text="z. B. B, E (Es), F, C — leer wenn keine Stimmung",
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(frame, text="Synonyme (OCR, mehrsprachig)").grid(row=4, column=1, sticky=tk.W, **padding)
        synonym_frame = ttk.Frame(frame)
        synonym_frame.grid(row=5, column=1, sticky=tk.NSEW, **padding)

        self.synonym_list = tk.Listbox(synonym_frame, height=9, exportselection=False)
        self.synonym_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        synonym_scroll = ttk.Scrollbar(synonym_frame, orient=tk.VERTICAL, command=self.synonym_list.yview)
        synonym_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.synonym_list.configure(yscrollcommand=synonym_scroll.set)

        add_row = ttk.Frame(frame)
        add_row.grid(row=6, column=1, sticky=tk.EW, **padding)
        ttk.Entry(add_row, textvariable=self.synonym_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(add_row, text="Hinzufügen", command=self._add_synonym).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(add_row, text="Entfernen", command=self._remove_synonym).pack(side=tk.LEFT)

        action_row = ttk.Frame(frame)
        action_row.grid(row=7, column=0, columnspan=2, sticky=tk.EW, **padding)
        ttk.Button(action_row, text="Standard wiederherstellen", command=self._restore_defaults).pack(side=tk.LEFT)
        ttk.Button(action_row, text="Abbrechen", command=self._cancel).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(action_row, text="Speichern", command=self._save).pack(side=tk.RIGHT)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        self._refresh_instrument_list()

    def _refresh_instrument_list(self, select_index: int | None = None) -> None:
        self.instrument_list.delete(0, tk.END)
        for instrument in self._instruments:
            self.instrument_list.insert(tk.END, self._format_list_label(instrument))

        if not self._instruments:
            self._selected_index = None
            self._clear_detail()
            return

        index = select_index if select_index is not None else (self._selected_index or 0)
        index = max(0, min(index, len(self._instruments) - 1))
        self.instrument_list.selection_clear(0, tk.END)
        self.instrument_list.selection_set(index)
        self._select_instrument(index)

    def _on_list_select(self, _event: object = None) -> None:
        selection = self.instrument_list.curselection()
        if not selection:
            return
        self._select_instrument(selection[0])

    def _select_instrument(self, index: int) -> None:
        self._selected_index = index
        instrument = self._instruments[index]

        self.name_var.trace_remove("write", self._name_trace)
        self.tuning_var.trace_remove("write", self._tuning_trace)
        self.name_var.set(instrument.name)
        self.tuning_var.set(instrument.tuning)
        self._name_trace = self.name_var.trace_add("write", lambda *_: self._sync_name())
        self._tuning_trace = self.tuning_var.trace_add("write", lambda *_: self._sync_tuning())

        self.synonym_list.delete(0, tk.END)
        for synonym in instrument.synonyms:
            if normalized_key(synonym) != normalized_key(instrument.name):
                self.synonym_list.insert(tk.END, synonym)

    def _clear_detail(self) -> None:
        self.name_var.set("")
        self.tuning_var.set("")
        self.synonym_list.delete(0, tk.END)

    def _current_instrument(self) -> Instrument | None:
        if self._selected_index is None or self._selected_index >= len(self._instruments):
            return None
        return self._instruments[self._selected_index]

    def _replace_current(self, instrument: Instrument) -> None:
        if self._selected_index is None:
            return
        self._instruments[self._selected_index] = instrument

    def _sync_name(self) -> None:
        instrument = self._current_instrument()
        if instrument is None or self._selected_index is None:
            return

        new_name = self.name_var.get().strip()
        if not new_name:
            return

        extra_synonyms = [s for s in instrument.synonyms if normalized_key(s) != normalized_key(instrument.name)]
        updated = Instrument(name=new_name, tuning=instrument.tuning, synonyms=(new_name, *extra_synonyms))
        self._replace_current(updated)
        self.instrument_list.delete(self._selected_index)
        self.instrument_list.insert(self._selected_index, self._format_list_label(updated))
        self.instrument_list.selection_set(self._selected_index)

    def _sync_tuning(self) -> None:
        instrument = self._current_instrument()
        if instrument is None:
            return
        updated = Instrument(
            name=instrument.name,
            tuning=self.tuning_var.get().strip().upper(),
            synonyms=instrument.synonyms,
        )
        self._replace_current(updated)
        self.instrument_list.delete(self._selected_index)
        self.instrument_list.insert(self._selected_index, self._format_list_label(updated))
        self.instrument_list.selection_set(self._selected_index)

    def _add_instrument(self) -> None:
        base = "Neues Instrument"
        name = base
        counter = 2
        existing = {normalized_key(item.name) for item in self._instruments}
        while normalized_key(name) in existing:
            name = f"{base} {counter}"
            counter += 1

        self._instruments.append(Instrument(name=name, tuning="", synonyms=(name,)))
        self._refresh_instrument_list(select_index=len(self._instruments) - 1)

    def _remove_instrument(self) -> None:
        if self._selected_index is None:
            return
        if not messagebox.askyesno("Löschen", "Ausgewähltes Instrument wirklich löschen?", parent=self):
            return

        index = self._selected_index
        del self._instruments[index]
        next_index = min(index, len(self._instruments) - 1) if self._instruments else None
        self._refresh_instrument_list(select_index=next_index)

    def _add_synonym(self) -> None:
        instrument = self._current_instrument()
        if instrument is None or self._selected_index is None:
            return

        synonym = self.synonym_var.get().strip()
        error = validate_synonym(synonym, instrument=instrument, all_instruments=self._instruments)
        if error:
            messagebox.showwarning("Synonym ungültig", error, parent=self)
            return

        updated = Instrument(name=instrument.name, tuning=instrument.tuning, synonyms=(*instrument.synonyms, synonym))
        self._replace_current(updated)
        self.synonym_var.set("")
        self._select_instrument(self._selected_index)

    def _remove_synonym(self) -> None:
        instrument = self._current_instrument()
        if instrument is None or self._selected_index is None:
            return

        selection = self.synonym_list.curselection()
        if not selection:
            return

        removable = [s for s in instrument.synonyms if normalized_key(s) != normalized_key(instrument.name)]
        synonym = removable[selection[0]]
        updated_synonyms = tuple(s for s in instrument.synonyms if s != synonym)
        self._replace_current(
            Instrument(name=instrument.name, tuning=instrument.tuning, synonyms=updated_synonyms)
        )
        self._select_instrument(self._selected_index)

    def _restore_defaults(self) -> None:
        if not messagebox.askyesno(
            "Standard wiederherstellen",
            "Alle benutzerdefinierten Instrumente und Synonyme werden überschrieben. Fortfahren?",
            parent=self,
        ):
            return
        self._instruments = copy.deepcopy(load_default_instruments())
        self._refresh_instrument_list(select_index=0)

    def _save(self) -> None:
        cleaned: list[Instrument] = []
        seen: set[str] = set()
        for instrument in self._instruments:
            name = instrument.name.strip()
            if not name:
                messagebox.showwarning("Ungültiger Eintrag", "Jedes Instrument braucht einen Namen.", parent=self)
                return
            key = normalized_key(name)
            if key in seen:
                messagebox.showwarning("Doppelter Name", f"„{name}“ ist mehrfach vorhanden.", parent=self)
                return
            seen.add(key)

            synonyms: list[str] = []
            for synonym in instrument.synonyms:
                candidate = synonym.strip()
                if not candidate:
                    continue
                error = validate_synonym(
                    candidate,
                    instrument=Instrument(name=name, tuning=instrument.tuning, synonyms=tuple(synonyms or [name])),
                    all_instruments=self._instruments,
                )
                if error and normalized_key(candidate) != normalized_key(name):
                    messagebox.showwarning("Synonym ungültig", f"„{candidate}“: {error}", parent=self)
                    return
                if normalized_key(candidate) not in {normalized_key(s) for s in synonyms}:
                    synonyms.append(candidate)

            if normalized_key(name) not in {normalized_key(s) for s in synonyms}:
                synonyms.insert(0, name)

            cleaned.append(
                Instrument(
                    name=name,
                    tuning=instrument.tuning.strip().upper(),
                    synonyms=tuple(synonyms),
                )
            )

        save_instruments(cleaned)
        self._on_save(cleaned)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
