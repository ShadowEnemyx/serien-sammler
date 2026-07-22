"""Cross-platform Tkinter desktop interface."""

from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from series_collector import __version__
from series_collector.core import (
    CollectorError,
    CopyProgress,
    CopySummary,
    ScanResult,
    copy_series,
    load_config,
    normalise_language,
    open_folder,
    save_config,
    scan_series,
)
from series_collector.i18n import translate


LANGUAGE_LABELS = {"de": "Deutsch", "en": "English"}


class SeriesCollectorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        config = load_config()
        self.language = normalise_language(config.get("language"))
        self.source = tk.StringVar(value=config.get("source", ""))
        self.destination = tk.StringVar(value=config.get("destination", ""))
        self.series_name = tk.StringVar()
        self.language_label = tk.StringVar(value=LANGUAGE_LABELS[self.language])
        self.summary_text = tk.StringVar()
        self.status_text = tk.StringVar()
        self.counter_text = tk.StringVar()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.current_scan: Optional[ScanResult] = None
        self.copying = False
        self.close_when_done = False

        self.geometry("820x620")
        self.minsize(700, 520)
        self._configure_style()
        self._build_ui()
        self._apply_language()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._process_events)

    def _configure_style(self) -> None:
        self.configure(background="#f3f4f6")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f3f4f6")
        style.configure("TLabel", background="#f3f4f6", foreground="#1f2937")
        style.configure("Header.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Summary.TLabel", font=("TkDefaultFont", 11, "bold"))
        style.configure("TButton", padding=(10, 7))
        style.configure("Treeview", rowheight=25)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(8, weight=1)

        self.title_label = ttk.Label(outer, style="Header.TLabel")
        self.title_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        self.language_label_widget = ttk.Label(outer)
        self.language_label_widget.grid(row=0, column=1, sticky="e", padx=(0, 8))
        self.language_box = ttk.Combobox(
            outer,
            textvariable=self.language_label,
            values=list(LANGUAGE_LABELS.values()),
            state="readonly",
            width=10,
        )
        self.language_box.grid(row=0, column=2, sticky="e")
        self.language_box.bind("<<ComboboxSelected>>", self._change_language)

        self.source_label = ttk.Label(outer)
        self.source_label.grid(row=1, column=0, columnspan=3, sticky="w")
        self.source_entry = ttk.Entry(outer, textvariable=self.source)
        self.source_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(3, 10))
        self.source_button = ttk.Button(outer, command=self._choose_source)
        self.source_button.grid(row=2, column=2, padx=(8, 0), pady=(3, 10))

        self.destination_label = ttk.Label(outer)
        self.destination_label.grid(row=3, column=0, columnspan=3, sticky="w")
        self.destination_entry = ttk.Entry(outer, textvariable=self.destination)
        self.destination_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(3, 10))
        self.destination_button = ttk.Button(outer, command=self._choose_destination)
        self.destination_button.grid(row=4, column=2, padx=(8, 0), pady=(3, 10))

        self.series_label = ttk.Label(outer)
        self.series_label.grid(row=5, column=0, columnspan=3, sticky="w")
        self.series_entry = ttk.Entry(outer, textvariable=self.series_name)
        self.series_entry.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(3, 12))
        self.series_entry.bind("<Return>", lambda _event: self._start_preview())

        actions = ttk.Frame(outer)
        actions.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.preview_button = ttk.Button(actions, command=self._start_preview)
        self.preview_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.copy_button = ttk.Button(actions, command=self._start_copy, state="disabled")
        self.copy_button.grid(row=0, column=1, sticky="ew", padx=4)
        self.cancel_button = ttk.Button(actions, command=self._cancel_copy, state="disabled")
        self.cancel_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        preview_frame = ttk.Frame(outer)
        preview_frame.grid(row=8, column=0, columnspan=3, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        self.summary_label = ttk.Label(preview_frame, textvariable=self.summary_text, style="Summary.TLabel")
        self.summary_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.tree = ttk.Treeview(preview_frame, columns=("status", "type", "file"), show="headings")
        self.tree.column("status", width=110, stretch=False)
        self.tree.column("type", width=100, stretch=False)
        self.tree.column("file", width=500, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 4))
        status_row = ttk.Frame(outer)
        status_row.grid(row=10, column=0, columnspan=3, sticky="ew")
        status_row.columnconfigure(0, weight=1)
        ttk.Label(status_row, textvariable=self.status_text).grid(row=0, column=0, sticky="w")
        ttk.Label(status_row, textvariable=self.counter_text).grid(row=0, column=1, sticky="e")

        for variable in (self.source, self.destination, self.series_name):
            variable.trace_add("write", self._inputs_changed)

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _apply_language(self) -> None:
        self.title(self._t("app_title"))
        self.title_label.configure(text=self._t("app_title"))
        self.language_label_widget.configure(text=self._t("language"))
        self.source_label.configure(text=self._t("source"))
        self.destination_label.configure(text=self._t("destination"))
        self.series_label.configure(text=self._t("series"))
        self.source_button.configure(text=self._t("browse"))
        self.destination_button.configure(text=self._t("browse"))
        self.preview_button.configure(text=self._t("preview"))
        self.copy_button.configure(text=self._t("copy"))
        self.cancel_button.configure(text=self._t("cancel"))
        self.tree.heading("status", text=self._t("column_status"))
        self.tree.heading("type", text=self._t("column_type"))
        self.tree.heading("file", text=self._t("column_file"))
        if self.current_scan:
            self._show_scan(self.current_scan)
        elif not self.copying:
            self.status_text.set(self._t("status_ready"))

    def _change_language(self, _event: object = None) -> None:
        selected = self.language_label.get()
        self.language = next(code for code, label in LANGUAGE_LABELS.items() if label == selected)
        try:
            save_config(language=self.language)
        except OSError:
            pass
        self._apply_language()

    def _inputs_changed(self, *_args: object) -> None:
        if self.copying:
            return
        self.current_scan = None
        self.copy_button.configure(state="disabled")
        self.summary_text.set("")
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _choose_source(self) -> None:
        path = filedialog.askdirectory(title=self._t("choose_source"), initialdir=self.source.get() or None)
        if path:
            self.source.set(path)

    def _choose_destination(self) -> None:
        path = filedialog.askdirectory(
            title=self._t("choose_destination"), initialdir=self.destination.get() or None
        )
        if path:
            self.destination.set(path)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.preview_button.configure(state=state)
        self.source_button.configure(state=state)
        self.destination_button.configure(state=state)
        self.source_entry.configure(state=state)
        self.destination_entry.configure(state=state)
        self.series_entry.configure(state=state)
        self.language_box.configure(state="disabled" if busy else "readonly")

    def _start_preview(self) -> None:
        if self.copying:
            return
        self._set_busy(True)
        self.copy_button.configure(state="disabled")
        self.status_text.set(self._t("status_scanning"))
        self.summary_text.set("")
        self.progress.configure(value=0, maximum=1)
        source = Path(self.source.get()).expanduser()
        destination = Path(self.destination.get()).expanduser()
        series_name = self.series_name.get()
        threading.Thread(
            target=self._preview_worker,
            args=(series_name, source, destination),
            daemon=True,
        ).start()

    def _preview_worker(self, series_name: str, source: Path, destination: Path) -> None:
        try:
            scan = scan_series(series_name, source, destination)
            self.events.put(("scan_complete", scan))
        except (CollectorError, OSError) as error:
            self.events.put(("scan_error", error))

    def _show_scan(self, scan: ScanResult) -> None:
        self.summary_text.set(
            self._t(
                "summary",
                videos=scan.video_count,
                subtitles=scan.subtitle_count,
                new=scan.new_count,
                existing=scan.existing_count,
            )
        )
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in scan.items:
            status = self._t("existing" if item.is_existing else "new")
            kind = self._t(item.kind)
            self.tree.insert("", "end", values=(status, kind, item.source.name))

    def _start_copy(self) -> None:
        if not self.current_scan or self.copying:
            return
        self.copying = True
        self.cancel_event.clear()
        self._set_busy(True)
        self.copy_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(value=0, maximum=max(len(self.current_scan.items), 1))
        self.counter_text.set(f"0 / {len(self.current_scan.items)}")
        threading.Thread(target=self._copy_worker, args=(self.current_scan,), daemon=True).start()

    def _copy_worker(self, scan: ScanResult) -> None:
        summary = copy_series(
            scan,
            progress_callback=lambda progress: self.events.put(("copy_progress", progress)),
            cancel_requested=self.cancel_event.is_set,
        )
        self.events.put(("copy_complete", summary))

    def _cancel_copy(self) -> None:
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_text.set(self._t("status_cancelling"))

    def _handle_error(self, error: object) -> None:
        if isinstance(error, CollectorError):
            message = self._t(error.code, **error.details)
        else:
            message = self._t("scan_failed", error=error)
        self.status_text.set(message)
        messagebox.showerror(self._t("error"), message, parent=self)

    def _handle_progress(self, progress: CopyProgress) -> None:
        self.progress.configure(value=progress.processed)
        self.counter_text.set(f"{progress.processed} / {progress.total}")
        self.status_text.set(self._t("status_copying", current=progress.current_file))

    def _handle_copy_complete(self, summary: CopySummary) -> None:
        self.copying = False
        self.cancel_button.configure(state="disabled")
        self._set_busy(False)
        try:
            save_config(
                source=Path(self.source.get()),
                destination=Path(self.destination.get()),
                language=self.language,
            )
        except OSError:
            pass

        if summary.cancelled:
            message = self._t("status_cancelled", copied=summary.copied, skipped=summary.skipped)
        else:
            message = self._t(
                "status_complete",
                copied=summary.copied,
                skipped=summary.skipped,
                failed=summary.failed,
            )
        self.status_text.set(message)
        if summary.failed:
            details = "\n".join(summary.errors[:8])
            messagebox.showwarning(
                self._t("warning"),
                f"{self._t('copy_failed', count=summary.failed)}\n\n{details}",
                parent=self,
            )
        elif not summary.cancelled:
            messagebox.showinfo(self._t("app_title"), message, parent=self)
            open_folder(summary.target)

        if self.close_when_done:
            self.destroy()
            return
        self._start_preview()

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "scan_complete":
                    self._set_busy(False)
                    self.current_scan = value
                    try:
                        save_config(
                            source=value.source,
                            destination=value.destination,
                            language=self.language,
                        )
                    except OSError:
                        pass
                    self._show_scan(value)
                    if value.items:
                        self.copy_button.configure(state="normal" if value.new_count else "disabled")
                        self.status_text.set(self.summary_text.get())
                    else:
                        self.status_text.set(self._t("no_matches"))
                        messagebox.showinfo(self._t("app_title"), self._t("no_matches"), parent=self)
                elif event == "scan_error":
                    self._set_busy(False)
                    self._handle_error(value)
                elif event == "copy_progress":
                    self._handle_progress(value)
                elif event == "copy_complete":
                    self._handle_copy_complete(value)
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _on_close(self) -> None:
        if self.copying:
            if not messagebox.askyesno(self._t("warning"), self._t("confirm_close"), parent=self):
                return
            self.close_when_done = True
            self._cancel_copy()
            return
        self.destroy()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--version", action="store_true")
    arguments, _unknown = parser.parse_known_args(argv)
    if arguments.version:
        print(__version__)
        return 0
    SeriesCollectorApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
