"""Platform-independent scanning, copying, and configuration logic."""

from __future__ import annotations

import json
import locale
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


VIDEO_EXTENSIONS = {".mkv", ".mp4"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | SUBTITLE_EXTENSIONS
MANIFEST_NAME = ".serien-sammler-manifest.json"
CONFIG_PATH = Path.home() / ".serien-sammler-config.json"


class CollectorError(Exception):
    def __init__(self, code: str, **details: str) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class ScanItem:
    source: Path
    kind: str
    existing_destination: Optional[Path]

    @property
    def is_existing(self) -> bool:
        return self.existing_destination is not None


@dataclass(frozen=True)
class ScanResult:
    series_name: str
    source: Path
    destination: Path
    target: Path
    items: tuple[ScanItem, ...]

    @property
    def video_count(self) -> int:
        return sum(item.kind == "video" for item in self.items)

    @property
    def subtitle_count(self) -> int:
        return sum(item.kind == "subtitle" for item in self.items)

    @property
    def new_count(self) -> int:
        return sum(not item.is_existing for item in self.items)

    @property
    def existing_count(self) -> int:
        return sum(item.is_existing for item in self.items)


@dataclass(frozen=True)
class CopyProgress:
    processed: int
    total: int
    current_file: str
    action: str
    copied: int
    skipped: int
    failed: int
    error: str = ""


@dataclass(frozen=True)
class CopySummary:
    target: Path
    total: int
    processed: int
    copied: int
    skipped: int
    failed: int
    cancelled: bool
    errors: tuple[str, ...]


def folder_name(name: str) -> str:
    return re.sub(r"[/:\\\x00]", " ", name).strip(" .")


def normalise_for_search(text: str) -> str:
    return "".join(character for character in text.casefold() if character.isalnum())


def default_language() -> str:
    language = locale.getlocale()[0] or ""
    return "de" if language.casefold().startswith("de") else "en"


def normalise_language(language: Optional[str]) -> str:
    return language if language in {"de", "en"} else default_language()


def free_name(folder: Path, name: str) -> Path:
    candidate = folder / name
    if not candidate.exists():
        return candidate

    stem, suffix = candidate.stem, candidate.suffix
    number = 2
    while True:
        candidate = folder / f"{stem} ({number}){suffix}"
        if not candidate.exists():
            return candidate
        number += 1


def source_signature(file: Path) -> dict[str, int | str]:
    stats = file.stat()
    return {
        "source": str(file.resolve()),
        "size": stats.st_size,
        "modified": stats.st_mtime_ns,
    }


def load_manifest(folder: Path) -> dict[str, dict[str, int | str]]:
    manifest_path = folder / MANIFEST_NAME
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            data = json.load(manifest_file)
        files = data.get("files", {})
        return files if isinstance(files, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_manifest(folder: Path, files: dict[str, dict[str, int | str]]) -> None:
    manifest_path = folder / MANIFEST_NAME
    temporary_path = folder / f"{MANIFEST_NAME}.tmp"
    with temporary_path.open("w", encoding="utf-8") as manifest_file:
        json.dump({"files": files}, manifest_file, ensure_ascii=False, indent=2)
    temporary_path.replace(manifest_path)


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, str]:
    try:
        with config_path.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return {}

    config: dict[str, str] = {}
    for key in ("source", "destination"):
        if isinstance(data.get(key), str):
            config[key] = data[key]
    if data.get("language") in {"de", "en"}:
        config["language"] = data["language"]
    return config


def save_config(
    source: Optional[Path] = None,
    destination: Optional[Path] = None,
    language: Optional[str] = None,
    config_path: Path = CONFIG_PATH,
) -> None:
    config = load_config(config_path)
    if source is not None:
        config["source"] = str(source.resolve())
    if destination is not None:
        config["destination"] = str(destination.resolve())
    if language in {"de", "en"}:
        config["language"] = language

    temporary_path = config_path.with_suffix(f"{config_path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
    temporary_path.replace(config_path)


def existing_destination(
    file: Path,
    signature: dict[str, int | str],
    target: Path,
    manifest: dict[str, dict[str, int | str]],
) -> Optional[Path]:
    source = str(signature["source"])
    record = manifest.get(source)
    if record and record.get("size") == signature["size"] and record.get("modified") == signature["modified"]:
        destination = target / str(record.get("destination", ""))
        if destination.is_file():
            return destination

    candidate = target / file.name
    if not manifest and candidate.is_file() and candidate.stat().st_size == signature["size"]:
        return candidate
    return None


def matching_files(source: Path, keyword: str) -> list[Path]:
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not path.name.startswith("._")
        and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        and keyword in normalise_for_search(path.name)
    )


def target_is_inside_source(source: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(source.resolve())
        return True
    except ValueError:
        return False


def scan_series(name_input: str, source: Path, destination: Path) -> ScanResult:
    series_name = folder_name(name_input)
    if not series_name:
        raise CollectorError("series_required")
    if not source.is_dir():
        raise CollectorError("source_missing", path=str(source))

    target = destination / series_name
    if target_is_inside_source(source, target):
        raise CollectorError("destination_inside_source")

    manifest = load_manifest(target)
    items: list[ScanItem] = []
    for file in matching_files(source, normalise_for_search(series_name)):
        signature = source_signature(file)
        existing = existing_destination(file, signature, target, manifest)
        kind = "video" if file.suffix.casefold() in VIDEO_EXTENSIONS else "subtitle"
        items.append(ScanItem(source=file, kind=kind, existing_destination=existing))

    return ScanResult(
        series_name=series_name,
        source=source,
        destination=destination,
        target=target,
        items=tuple(items),
    )


def copy_series(
    scan: ScanResult,
    progress_callback: Optional[Callable[[CopyProgress], None]] = None,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> CopySummary:
    scan.target.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(scan.target)
    copied = 0
    skipped = 0
    failed = 0
    processed = 0
    cancelled = False
    errors: list[str] = []

    for item in scan.items:
        if cancel_requested and cancel_requested():
            cancelled = True
            break

        action = "copied"
        error_text = ""
        try:
            signature = source_signature(item.source)
            source_key = str(signature["source"])
            output_path = existing_destination(item.source, signature, scan.target, manifest)
            if output_path:
                manifest[source_key] = {**signature, "destination": output_path.name}
                save_manifest(scan.target, manifest)
                skipped += 1
                action = "skipped"
            else:
                output_path = free_name(scan.target, item.source.name)
                shutil.copy2(item.source, output_path)
                manifest[source_key] = {**signature, "destination": output_path.name}
                save_manifest(scan.target, manifest)
                copied += 1
        except OSError as error:
            failed += 1
            action = "failed"
            error_text = f"{item.source.name}: {error}"
            errors.append(error_text)

        processed += 1
        if progress_callback:
            progress_callback(
                CopyProgress(
                    processed=processed,
                    total=len(scan.items),
                    current_file=item.source.name,
                    action=action,
                    copied=copied,
                    skipped=skipped,
                    failed=failed,
                    error=error_text,
                )
            )

    return CopySummary(
        target=scan.target,
        total=len(scan.items),
        processed=processed,
        copied=copied,
        skipped=skipped,
        failed=failed,
        cancelled=cancelled,
        errors=tuple(errors),
    )


def open_folder(folder: Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        elif os.name == "nt":
            os.startfile(str(folder))
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", str(folder)], check=False)
    except OSError:
        pass
