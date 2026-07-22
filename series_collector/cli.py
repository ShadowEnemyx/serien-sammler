"""Command-line interface for Series Collector."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from series_collector import __version__
from series_collector.core import (
    CollectorError,
    CopyProgress,
    copy_series,
    load_config,
    normalise_language,
    open_folder,
    save_config,
    scan_series,
)
from series_collector.i18n import translate


def _error_message(language: str, error: CollectorError) -> str:
    return translate(language, error.code, **error.details)


def _print_preview(language: str, scan: object) -> None:
    print(
        translate(
            language,
            "cli_preview",
            videos=scan.video_count,
            subtitles=scan.subtitle_count,
            new=scan.new_count,
            existing=scan.existing_count,
            target=scan.target,
        )
    )


def _progress_printer(language: str, progress: CopyProgress) -> None:
    key = {"copied": "cli_copy", "skipped": "cli_skip", "failed": "cli_fail"}[progress.action]
    print(
        translate(
            language,
            key,
            current=progress.processed,
            total=progress.total,
            file=progress.current_file,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect series files in one folder.")
    parser.add_argument("--series", help="Series name or search term")
    parser.add_argument("--source", help="Folder to search recursively")
    parser.add_argument("--destination", help="Parent folder for the series folder")
    parser.add_argument("--preview", action="store_true", help="Show planned changes without copying")
    parser.add_argument("--remember-folders", action="store_true", help="Remember source and destination")
    parser.add_argument("--language", choices=("de", "en"), help="Interface language")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("--config-value", choices=("source", "destination", "language"), help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.version:
        print(__version__)
        return 0

    config = load_config()
    if arguments.config_value:
        print(config.get(arguments.config_value, ""))
        return 0

    language = normalise_language(arguments.language or config.get("language"))
    series_name = arguments.series
    if series_name is None:
        try:
            series_name = input(translate(language, "prompt_series")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

    source_value = arguments.source or config.get("source")
    destination_value = arguments.destination or config.get("destination")
    if not source_value or not destination_value:
        print(translate(language, "folders_required"), file=sys.stderr)
        return 2

    source = Path(source_value).expanduser()
    destination = Path(destination_value).expanduser()
    try:
        scan = scan_series(series_name, source, destination)
    except (CollectorError, OSError) as error:
        message = _error_message(language, error) if isinstance(error, CollectorError) else str(error)
        print(message, file=sys.stderr)
        return 2

    if not scan.items:
        print(translate(language, "cli_no_matches"))
        return 1
    if arguments.preview:
        _print_preview(language, scan)
        return 0

    summary = copy_series(scan, progress_callback=lambda progress: _progress_printer(language, progress))
    print(
        translate(
            language,
            "cli_done",
            copied=summary.copied,
            skipped=summary.skipped,
            failed=summary.failed,
        )
    )
    print(summary.target)

    if arguments.remember_folders and summary.failed == 0:
        try:
            save_config(source=source, destination=destination, language=language)
        except OSError as error:
            print(translate(language, "config_warning", error=error), file=sys.stderr)
    if summary.processed:
        open_folder(summary.target)
    return 2 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
