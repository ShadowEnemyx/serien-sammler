"""Cross-platform Tkinter desktop interface."""

from __future__ import annotations

import argparse
import logging
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from series_collector import __version__
from series_collector.core import (
    CollectorError,
    CopyProgress,
    CopySummary,
    ScanItem,
    ScanResult,
    copy_series,
    load_config,
    normalise_language,
    open_folder,
    save_config,
    scan_series,
)
from series_collector.i18n import translate
from series_collector.logging_utils import configure_logging, save_diagnostic_report
from series_collector.updates import UpdateInfo, check_for_updates, update_check_due


LANGUAGE_LABELS = {"de": "Deutsch", "en": "English"}
logger = logging.getLogger("series_collector")


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative


class SeriesCollectorApp(tk.Tk):
    def __init__(self, log_path: Optional[Path] = None) -> None:
        super().__init__()
        config = load_config()
        self.log_path = log_path or configure_logging()
        self.language = normalise_language(str(config.get("language", "")))
        self.source = tk.StringVar(value=str(config.get("source", "")))
        self.destination = tk.StringVar(value=str(config.get("destination", "")))
        self.series_name = tk.StringVar()
        self.language_label = tk.StringVar(value=LANGUAGE_LABELS[self.language])
        self.check_updates = tk.BooleanVar(value=bool(config.get("check_updates", True)))
        self.summary_text = tk.StringVar()
        self.status_text = tk.StringVar()
        self.counter_text = tk.StringVar()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.current_scan: Optional[ScanResult] = None
        self.row_items: dict[str, ScanItem] = {}
        self.selected_sources: set[str] = set()
        self.copying = False
        self.close_when_done = False
        self.update_check_running = False
        self._icon: Optional[tk.PhotoImage] = None

        self.geometry("1080x700")
        self.minsize(820, 560)
        self._configure_style()
        self._set_icon()
        self._build_ui()
        self._apply_language()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._process_events)
        if self.check_updates.get() and update_check_due(str(config.get("last_update_check", ""))):
            self.after(800, lambda: self._start_update_check(manual=False))

    def _set_icon(self) -> None:
        try:
            self._icon = tk.PhotoImage(file=str(resource_path("assets/app-icon.png")))
            self.iconphoto(True, self._icon)
        except tk.TclError:
            logger.warning("Application icon could not be loaded")

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
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 14))
        self.language_label_widget = ttk.Label(outer)
        self.language_label_widget.grid(row=0, column=1, sticky="e", padx=(0, 8))
        self.language_box = ttk.Combobox(
            outer, textvariable=self.language_label, values=list(LANGUAGE_LABELS.values()), state="readonly", width=10
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

        columns = ("selected", "action", "season", "quality", "type", "file", "path")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.column("selected", width=64, stretch=False, anchor="center")
        self.tree.column("action", width=110, stretch=False)
        self.tree.column("season", width=70, stretch=False, anchor="center")
        self.tree.column("quality", width=105, stretch=False)
        self.tree.column("type", width=85, stretch=False)
        self.tree.column("file", width=260, stretch=True)
        self.tree.column("path", width=360, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._toggle_selected)
        self.tree.bind("<space>", self._toggle_selected)
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

        utilities = ttk.Frame(outer)
        utilities.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.update_checkbox = ttk.Checkbutton(
            utilities, variable=self.check_updates, command=self._save_update_preference
        )
        self.update_checkbox.grid(row=0, column=0, sticky="w")
        self.update_button = ttk.Button(utilities, command=lambda: self._start_update_check(manual=True))
        self.update_button.grid(row=0, column=1, padx=(10, 4))
        self.log_button = ttk.Button(utilities, command=lambda: open_folder(self.log_path.parent))
        self.log_button.grid(row=0, column=2, padx=4)
        self.diagnostic_button = ttk.Button(utilities, command=self._save_diagnostics)
        self.diagnostic_button.grid(row=0, column=3, padx=(4, 0))

        for variable in (self.source, self.destination, self.series_name):
            variable.trace_add("write", self._inputs_changed)

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _apply_language(self) -> None:
        self.title(self._t("app_title"))
        self.title_label.configure(text=f"{self._t('app_title')} {__version__}")
        self.language_label_widget.configure(text=self._t("language"))
        self.source_label.configure(text=self._t("source"))
        self.destination_label.configure(text=self._t("destination"))
        self.series_label.configure(text=self._t("series"))
        self.source_button.configure(text=self._t("browse"))
        self.destination_button.configure(text=self._t("browse"))
        self.preview_button.configure(text=self._t("preview"))
        self.copy_button.configure(text=self._t("copy"))
        self.cancel_button.configure(text=self._t("cancel"))
        for column in ("selected", "action", "season", "quality", "type", "file", "path"):
            self.tree.heading(column, text=self._t(f"column_{column}"))
        self.update_checkbox.configure(text=self._t("check_updates_startup"))
        self.update_button.configure(text=self._t("check_updates_now"))
        self.log_button.configure(text=self._t("open_log"))
        self.diagnostic_button.configure(text=self._t("save_diagnostics"))
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

    def _save_update_preference(self) -> None:
        try:
            save_config(check_updates=self.check_updates.get())
        except OSError:
            pass

    def _inputs_changed(self, *_args: object) -> None:
        if self.copying:
            return
        self.current_scan = None
        self.selected_sources.clear()
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
        for widget in (
            self.preview_button,
            self.source_button,
            self.destination_button,
            self.source_entry,
            self.destination_entry,
            self.series_entry,
        ):
            widget.configure(state=state)
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
        threading.Thread(
            target=self._preview_worker,
            args=(self.series_name.get(), source, destination),
            daemon=True,
        ).start()

    def _preview_worker(self, series_name: str, source: Path, destination: Path) -> None:
        try:
            self.events.put(("scan_complete", scan_series(series_name, source, destination)))
        except (CollectorError, OSError) as error:
            self.events.put(("scan_error", error))

    def _show_scan(self, scan: ScanResult) -> None:
        self.summary_text.set(
            self._t(
                "summary",
                videos=scan.video_count,
                subtitles=scan.subtitle_count,
                new=scan.new_count,
                moved=scan.move_count,
                existing=scan.existing_count,
                ambiguous=scan.ambiguous_count,
            )
        )
        self.row_items.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.selected_sources = {str(item.source) for item in scan.items if item.selected}
        for item in scan.items:
            row = self.tree.insert(
                "",
                "end",
                values=(
                    "✓" if item.selected else "—",
                    self._t(item.destination_action),
                    item.season_label,
                    self._t(item.match_quality),
                    self._t(item.kind),
                    item.source.name,
                    str(item.source.parent),
                ),
            )
            self.row_items[row] = item
        self._refresh_copy_button()

    def _toggle_selected(self, event: object = None) -> None:
        if self.copying:
            return
        row = self.tree.identify_row(getattr(event, "y", 0)) if getattr(event, "y", None) is not None else ""
        if not row:
            selection = self.tree.selection()
            row = selection[0] if selection else ""
        item = self.row_items.get(row)
        if not item or not item.requires_change:
            return
        source = str(item.source)
        if source in self.selected_sources:
            self.selected_sources.remove(source)
            selected_label = "—"
        else:
            self.selected_sources.add(source)
            selected_label = "✓"
        values = list(self.tree.item(row, "values"))
        values[0] = selected_label
        self.tree.item(row, values=values)
        self._refresh_copy_button()

    def _refresh_copy_button(self) -> None:
        enabled = bool(
            self.current_scan
            and any(item.requires_change and str(item.source) in self.selected_sources for item in self.current_scan.items)
        )
        self.copy_button.configure(state="normal" if enabled and not self.copying else "disabled")

    def _start_copy(self) -> None:
        if not self.current_scan or self.copying:
            return
        scan = self.current_scan.with_selection(Path(path) for path in self.selected_sources)
        selected_count = sum(item.selected for item in scan.items)
        if not selected_count:
            return
        self.copying = True
        self.cancel_event.clear()
        self._set_busy(True)
        self.copy_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(value=0, maximum=max(selected_count, 1))
        self.counter_text.set(f"0 / {selected_count}")
        threading.Thread(target=self._copy_worker, args=(scan,), daemon=True).start()

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
        self._save_settings()
        if summary.cancelled:
            message = self._t(
                "status_cancelled", copied=summary.copied, moved=summary.moved, skipped=summary.skipped
            )
        else:
            message = self._t(
                "status_complete",
                copied=summary.copied,
                moved=summary.moved,
                skipped=summary.skipped,
                failed=summary.failed,
            )
        self.status_text.set(message)
        if summary.failed:
            details = "\n".join(summary.errors[:8])
            messagebox.showwarning(
                self._t("warning"), f"{self._t('copy_failed', count=summary.failed)}\n\n{details}", parent=self
            )
        elif not summary.cancelled:
            messagebox.showinfo(self._t("app_title"), message, parent=self)
            open_folder(summary.target)
        if self.close_when_done:
            self.destroy()
            return
        self._start_preview()

    def _save_settings(self) -> None:
        try:
            save_config(
                source=Path(self.source.get()),
                destination=Path(self.destination.get()),
                language=self.language,
                check_updates=self.check_updates.get(),
            )
        except OSError:
            logger.exception("Could not save settings")

    def _start_update_check(self, manual: bool) -> None:
        if self.update_check_running:
            return
        self.update_check_running = True
        self.update_button.configure(state="disabled")
        if manual:
            self.status_text.set(self._t("checking_updates"))
        threading.Thread(target=self._update_worker, args=(manual,), daemon=True).start()

    def _update_worker(self, manual: bool) -> None:
        try:
            self.events.put(("update_complete", (manual, check_for_updates())))
        except Exception as error:  # network and malformed remote response
            logger.warning("Update check failed: %s", error)
            self.events.put(("update_error", (manual, error)))

    def _handle_update_complete(self, manual: bool, info: UpdateInfo) -> None:
        self.update_check_running = False
        self.update_button.configure(state="normal")
        try:
            save_config(last_update_check=datetime.now(timezone.utc).isoformat())
        except OSError:
            pass
        if info.available:
            if messagebox.askyesno(
                self._t("update_available_title"),
                self._t("update_available", current=info.current_version, latest=info.latest_version),
                parent=self,
            ):
                webbrowser.open(info.release_url)
        elif manual:
            messagebox.showinfo(self._t("updates"), self._t("up_to_date", version=__version__), parent=self)
        if manual:
            self.status_text.set(self._t("status_ready"))

    def _save_diagnostics(self) -> None:
        filename = filedialog.asksaveasfilename(
            title=self._t("save_diagnostics"),
            defaultextension=".txt",
            initialfile=f"Serien-Sammler-Diagnose-{__version__}.txt",
            filetypes=((self._t("text_files"), "*.txt"),),
        )
        if not filename:
            return
        try:
            save_diagnostic_report(Path(filename), self.log_path)
            messagebox.showinfo(self._t("app_title"), self._t("diagnostics_saved"), parent=self)
        except OSError as error:
            messagebox.showerror(self._t("error"), str(error), parent=self)

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "scan_complete":
                    self._set_busy(False)
                    self.current_scan = value
                    self._save_settings()
                    self._show_scan(value)
                    if value.items:
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
                elif event == "update_complete":
                    manual, info = value
                    self._handle_update_complete(manual, info)
                elif event == "update_error":
                    manual, error = value
                    self.update_check_running = False
                    self.update_button.configure(state="normal")
                    if manual:
                        messagebox.showwarning(
                            self._t("updates"), self._t("update_failed", error=error), parent=self
                        )
                        self.status_text.set(self._t("status_ready"))
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
    parser.add_argument("--log-file")
    arguments, _unknown = parser.parse_known_args(argv)
    if arguments.version:
        print(__version__)
        return 0
    log_path = configure_logging(Path(arguments.log_file) if arguments.log_file else None)
    SeriesCollectorApp(log_path=log_path).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
