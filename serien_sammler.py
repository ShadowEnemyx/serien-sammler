#!/usr/bin/env python3
"""Backward-compatible command-line entry point."""

from series_collector.cli import main
from series_collector.core import (
    CONFIG_PATH,
    MANIFEST_NAME,
    SUBTITLE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    VIDEO_EXTENSIONS,
    CollectorError,
    CopyProgress,
    CopySummary,
    ScanItem,
    ScanResult,
    copy_series,
    default_language,
    existing_destination,
    folder_name,
    free_name,
    load_config,
    load_manifest,
    matching_files,
    normalise_for_search,
    normalise_language,
    open_folder,
    save_config,
    save_manifest,
    scan_series,
    source_signature,
    target_is_inside_source,
)


if __name__ == "__main__":
    raise SystemExit(main())
