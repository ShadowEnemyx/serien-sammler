"""Platform-independent scanning, copying, and configuration logic."""

from __future__ import annotations

import hashlib
import json
import locale
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional
from uuid import uuid4


VIDEO_EXTENSIONS = {".mkv", ".mp4"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | SUBTITLE_EXTENSIONS
MANIFEST_NAME = ".serien-sammler-manifest.json"
MANIFEST_VERSION = 2
CONFIG_PATH = Path.home() / ".serien-sammler-config.json"
FINGERPRINT_SAMPLE_SIZE = 1024 * 1024
logger = logging.getLogger("series_collector")


class CollectorError(Exception):
    def __init__(self, code: str, **details: str) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    sample_sha256: str

    @property
    def key(self) -> str:
        return f"{self.size}:{self.sample_sha256}"


@dataclass(frozen=True)
class ScanItem:
    source: Path
    kind: str
    existing_destination: Optional[Path]
    fingerprint: FileFingerprint
    match_quality: str
    planned_destination: Path
    selected: bool = True
    duplicate_in_scan: bool = False

    @property
    def is_existing(self) -> bool:
        return self.existing_destination is not None

    @property
    def is_duplicate(self) -> bool:
        return self.is_existing or self.duplicate_in_scan

    @property
    def destination_action(self) -> str:
        if self.is_duplicate:
            return "action_duplicate"
        return "action_rename" if self.planned_destination.name != self.source.name else "action_copy"


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
        return sum(not item.is_duplicate for item in self.items)

    @property
    def selected_new_count(self) -> int:
        return sum(item.selected and not item.is_duplicate for item in self.items)

    @property
    def existing_count(self) -> int:
        return sum(item.is_duplicate for item in self.items)

    @property
    def ambiguous_count(self) -> int:
        return sum(item.match_quality == "ambiguous" for item in self.items)

    def with_selection(self, selected_sources: Iterable[Path]) -> "ScanResult":
        selected = {str(path) for path in selected_sources}
        return replace(
            self,
            items=tuple(
                replace(item, selected=str(item.source) in selected and not item.is_duplicate)
                for item in self.items
            ),
        )


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


def free_name(folder: Path, name: str, reserved: Optional[set[str]] = None) -> Path:
    reserved = reserved or set()
    candidate = folder / name
    if not candidate.exists() and candidate.name.casefold() not in reserved:
        return candidate

    stem, suffix = candidate.stem, candidate.suffix
    number = 2
    while True:
        candidate = folder / f"{stem} ({number}){suffix}"
        if not candidate.exists() and candidate.name.casefold() not in reserved:
            return candidate
        number += 1


def fast_fingerprint(file: Path, sample_size: int = FINGERPRINT_SAMPLE_SIZE) -> FileFingerprint:
    """Hash a small file fully, or the beginning/middle/end of a large file."""
    size = file.stat().st_size
    digest = hashlib.sha256()
    digest.update(size.to_bytes(16, "big"))
    with file.open("rb") as stream:
        if size <= sample_size * 3:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        else:
            positions = (0, max((size - sample_size) // 2, 0), max(size - sample_size, 0))
            for position in positions:
                stream.seek(position)
                digest.update(position.to_bytes(16, "big"))
                digest.update(stream.read(sample_size))
    return FileFingerprint(size=size, sample_sha256=digest.hexdigest())


def fingerprint_key(file: Path, fingerprint: FileFingerprint) -> str:
    """Keep byte-identical files with different media formats distinct."""
    return f"{file.suffix.casefold()}:{fingerprint.key}"


def source_signature(file: Path) -> dict[str, int | str]:
    """Legacy-compatible source metadata used in manifest source history."""
    stats = file.stat()
    return {"source": str(file.resolve()), "size": stats.st_size, "modified": stats.st_mtime_ns}


def _empty_manifest() -> dict[str, object]:
    return {"schema_version": MANIFEST_VERSION, "files": {}}


def load_manifest(folder: Path) -> dict[str, object]:
    manifest_path = folder / MANIFEST_NAME
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            data = json.load(manifest_file)
    except FileNotFoundError:
        return _empty_manifest()
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Could not read manifest %s: %s", manifest_path, error)
        return {**_empty_manifest(), "_corrupt": True}

    files = data.get("files", {}) if isinstance(data, dict) else {}
    if not isinstance(files, dict):
        files = {}
    if data.get("schema_version") == MANIFEST_VERSION:
        return {"schema_version": MANIFEST_VERSION, "files": files}
    return {"schema_version": 1, "legacy_files": files, "files": {}}


def _backup_corrupt_manifest(folder: Path, manifest: dict[str, object]) -> None:
    if not manifest.get("_corrupt"):
        return
    manifest_path = folder / MANIFEST_NAME
    if not manifest_path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = folder / f"{MANIFEST_NAME}.corrupt-{timestamp}"
    try:
        manifest_path.replace(backup)
        logger.warning("Backed up corrupt manifest to %s", backup)
    except OSError as error:
        logger.warning("Could not back up corrupt manifest %s: %s", manifest_path, error)


def save_manifest(folder: Path, manifest: dict[str, object]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / MANIFEST_NAME
    temporary_path = folder / f"{MANIFEST_NAME}.tmp"
    payload = {"schema_version": MANIFEST_VERSION, "files": manifest.get("files", {})}
    with temporary_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(payload, manifest_file, ensure_ascii=False, indent=2)
    temporary_path.replace(manifest_path)


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, object]:
    try:
        with config_path.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return {}

    config: dict[str, object] = {}
    for key in ("source", "destination", "last_update_check"):
        if isinstance(data.get(key), str):
            config[key] = data[key]
    if data.get("language") in {"de", "en"}:
        config["language"] = data["language"]
    if isinstance(data.get("check_updates"), bool):
        config["check_updates"] = data["check_updates"]
    return config


def save_config(
    source: Optional[Path] = None,
    destination: Optional[Path] = None,
    language: Optional[str] = None,
    check_updates: Optional[bool] = None,
    last_update_check: Optional[str] = None,
    config_path: Path = CONFIG_PATH,
) -> None:
    config = load_config(config_path)
    if source is not None:
        config["source"] = str(source.resolve())
    if destination is not None:
        config["destination"] = str(destination.resolve())
    if language in {"de", "en"}:
        config["language"] = language
    if check_updates is not None:
        config["check_updates"] = check_updates
    if last_update_check is not None:
        config["last_update_check"] = last_update_check

    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(f"{config_path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
    temporary_path.replace(config_path)


def classify_match(filename: str, keyword: str) -> Optional[str]:
    compact_name = normalise_for_search(Path(filename).stem)
    compact_keyword = normalise_for_search(keyword)
    if not compact_keyword or compact_keyword not in compact_name:
        return None
    start = compact_name.find(compact_keyword)
    remainder = compact_name[start + len(compact_keyword) :]
    if not remainder:
        return "exact"
    if re.match(r"^(?:s\d{1,3}(?:e\d{1,4})?|e\d{1,4}|season\d|staffel\d|\d{3,4}p|\d{4}(?:\D|$))", remainder):
        return "exact"

    separated_name = re.sub(r"[^\w]+", " ", Path(filename).stem.casefold(), flags=re.UNICODE).strip()
    separated_keyword = re.sub(r"[^\w]+", " ", keyword.casefold(), flags=re.UNICODE).strip()
    if separated_keyword and re.search(rf"(?<!\w){re.escape(separated_keyword)}(?!\w)", separated_name):
        return "likely"
    return "ambiguous"


def matching_files(source: Path, keyword: str) -> list[Path]:
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not path.name.startswith("._")
        and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        and classify_match(path.name, keyword) is not None
    )


def target_is_inside_source(source: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(source.resolve())
        return True
    except ValueError:
        return False


def _target_index(target: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not target.is_dir():
        return index
    for path in sorted(target.iterdir()):
        if not path.is_file() or path.name.startswith(".") or path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            fingerprint = fast_fingerprint(path)
            index.setdefault(fingerprint_key(path, fingerprint), path)
        except OSError as error:
            logger.warning("Could not fingerprint destination %s: %s", path, error)
    return index


def scan_series(name_input: str, source: Path, destination: Path) -> ScanResult:
    series_name = folder_name(name_input)
    if not series_name:
        raise CollectorError("series_required")
    if not source.is_dir():
        raise CollectorError("source_missing", path=str(source))

    target = destination / series_name
    if target_is_inside_source(source, target):
        raise CollectorError("destination_inside_source")

    target_index = _target_index(target)
    planned_fingerprints: dict[str, Path] = {}
    reserved = {path.name.casefold() for path in target.iterdir()} if target.is_dir() else set()
    items: list[ScanItem] = []
    for file in matching_files(source, series_name):
        fingerprint = fast_fingerprint(file)
        content_key = fingerprint_key(file, fingerprint)
        existing = target_index.get(content_key)
        duplicate_in_scan = existing is None and content_key in planned_fingerprints
        planned = existing or planned_fingerprints.get(content_key) or free_name(target, file.name, reserved)
        if not existing and not duplicate_in_scan:
            reserved.add(planned.name.casefold())
            planned_fingerprints[content_key] = planned
        quality = classify_match(file.name, series_name) or "ambiguous"
        kind = "video" if file.suffix.casefold() in VIDEO_EXTENSIONS else "subtitle"
        items.append(
            ScanItem(
                source=file,
                kind=kind,
                existing_destination=existing,
                fingerprint=fingerprint,
                match_quality=quality,
                planned_destination=planned,
                selected=quality != "ambiguous" and not duplicate_in_scan,
                duplicate_in_scan=duplicate_in_scan,
            )
        )

    return ScanResult(
        series_name=series_name,
        source=source,
        destination=destination,
        target=target,
        items=tuple(items),
    )


def _record_manifest_file(
    manifest: dict[str, object], fingerprint: FileFingerprint, destination: Path, source: Path
) -> None:
    files = manifest.setdefault("files", {})
    assert isinstance(files, dict)
    content_key = fingerprint_key(source, fingerprint)
    record = files.setdefault(
        content_key,
        {
            "size": fingerprint.size,
            "sample_sha256": fingerprint.sample_sha256,
            "destination": destination.name,
            "sources": {},
        },
    )
    if not isinstance(record, dict):
        record = {}
        files[content_key] = record
    record.update(
        {
            "size": fingerprint.size,
            "sample_sha256": fingerprint.sample_sha256,
            "destination": destination.name,
        }
    )
    sources = record.setdefault("sources", {})
    if isinstance(sources, dict):
        signature = source_signature(source)
        sources[str(signature["source"])] = {"modified": signature["modified"]}


def copy_series(
    scan: ScanResult,
    progress_callback: Optional[Callable[[CopyProgress], None]] = None,
    cancel_requested: Optional[Callable[[], bool]] = None,
) -> CopySummary:
    scan.target.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(scan.target)
    _backup_corrupt_manifest(scan.target, manifest)
    manifest["schema_version"] = MANIFEST_VERSION
    target_index = _target_index(scan.target)
    selected_items = tuple(item for item in scan.items if item.selected)
    copied = skipped = failed = processed = 0
    cancelled = False
    errors: list[str] = []

    for item in selected_items:
        if cancel_requested and cancel_requested():
            cancelled = True
            break

        action = "copied"
        error_text = ""
        temporary_path: Optional[Path] = None
        try:
            current_fingerprint = fast_fingerprint(item.source)
            if current_fingerprint != item.fingerprint:
                raise OSError("source file changed after the preview")

            content_key = fingerprint_key(item.source, current_fingerprint)
            output_path = target_index.get(content_key)
            if output_path and output_path.is_file():
                skipped += 1
                action = "skipped"
            else:
                output_path = item.planned_destination
                if output_path.exists():
                    output_path = free_name(scan.target, item.source.name)
                temporary_path = scan.target / f".{output_path.name}.{uuid4().hex}.partial"
                logger.info("Copying %s to %s", item.source, output_path)
                shutil.copy2(item.source, temporary_path)
                if fast_fingerprint(temporary_path) != current_fingerprint:
                    raise OSError("copied file failed fingerprint verification")
                temporary_path.replace(output_path)
                temporary_path = None
                target_index[content_key] = output_path
                copied += 1

            _record_manifest_file(manifest, current_fingerprint, output_path, item.source)
            save_manifest(scan.target, manifest)
        except OSError as error:
            failed += 1
            action = "failed"
            error_text = f"{item.source.name}: {error}"
            errors.append(error_text)
            logger.exception("Could not process %s", item.source)
            if temporary_path and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    logger.warning("Could not remove partial file %s", temporary_path)

        processed += 1
        if progress_callback:
            progress_callback(
                CopyProgress(
                    processed=processed,
                    total=len(selected_items),
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
        total=len(selected_items),
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
