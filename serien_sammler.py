#!/usr/bin/env python3
"""Sammelt Folgen einer Serie in einem einzigen Ordner."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


VIDEO_ENDUNGEN = {".mkv", ".mp4"}
MANIFEST_NAME = ".serien-sammler-manifest.json"


def folder_name(name: str) -> str:
    """Erstellt einen sicheren Ordnernamen aus der Benutzereingabe."""
    return re.sub(r"[/:\\\x00]", " ", name).strip(" .")


def normalise_for_search(text: str) -> str:
    """Ignoriert bei der Suche Leerzeichen und Satzzeichen."""
    return "".join(character for character in text.casefold() if character.isalnum())


def free_name(folder: Path, name: str) -> Path:
    """Verhindert, dass bereits vorhandene Dateien überschrieben werden."""
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


def existing_destination(
    file: Path, signature: dict[str, int | str], target: Path, manifest: dict[str, dict[str, int | str]]
) -> Path | None:
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


def matching_videos(source: Path, keyword: str) -> list[Path]:
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not path.name.startswith("._")
        and path.suffix.casefold() in VIDEO_ENDUNGEN
        and keyword in normalise_for_search(path.name)
    )


def open_folder(folder: Path) -> None:
    """Öffnet den Zielordner im Dateimanager des jeweiligen Betriebssystems."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        elif os.name == "nt":
            os.startfile(str(folder))
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", str(folder)], check=False)
    except OSError:
        pass


def collect_series(name_input: str, source: Path, destination: Path) -> int:
    series_name = folder_name(name_input)
    if not series_name:
        print("Fehler: Bitte einen Seriennamen eingeben.", file=sys.stderr)
        return 2
    if not source.is_dir():
        print(f"Fehler: Quellordner nicht gefunden: {source}", file=sys.stderr)
        return 2

    target = destination / series_name
    print(f"Suche nach „{series_name}“ in: {source}")
    files = matching_videos(source, normalise_for_search(series_name))
    if not files:
        print("Keine passenden .mkv- oder .mp4-Dateien gefunden.")
        return 1

    target.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(target)
    copied = 0
    skipped = 0
    errors: list[str] = []
    for number, file in enumerate(files, start=1):
        try:
            signature = source_signature(file)
            source = str(signature["source"])
            destination = existing_destination(file, signature, target, manifest)
            if destination:
                manifest[source] = {**signature, "destination": destination.name}
                save_manifest(target, manifest)
                skipped += 1
                print(f"Überspringe {number} von {len(files)} (bereits vorhanden): {file.name}")
                continue

            destination = free_name(target, file.name)
            print(f"Kopiere {number} von {len(files)}: {file.name}")
            shutil.copy2(file, destination)
            manifest[source] = {**signature, "destination": destination.name}
            save_manifest(target, manifest)
            copied += 1
        except OSError as error:
            errors.append(f"{file.name}: {error}")

    if copied or skipped:
        print(f"\nFertig: {copied} neue Datei(en) kopiert, {skipped} bereits vorhandene übersprungen.")
        print(f"Zielordner: {target}")
        open_folder(target)
    if errors:
        print(f"\n{len(errors)} Datei(en) konnten nicht kopiert werden:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sammelt Serienfolgen in einem Ordner.")
    parser.add_argument("--series", help="Name oder Stichwort der gewünschten Serie")
    parser.add_argument("--source", help="Ordner, der inklusive Unterordnern durchsucht wird")
    parser.add_argument("--destination", help="Oberordner für den neuen Serienordner")
    arguments = parser.parse_args()

    series_name = arguments.series
    if series_name is None:
        try:
            series_name = input("Name der Serie: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
    if not arguments.source or not arguments.destination:
        print("Fehler: Bitte Quell- und Zielordner angeben.", file=sys.stderr)
        return 2
    return collect_series(series_name, Path(arguments.source), Path(arguments.destination))


if __name__ == "__main__":
    raise SystemExit(main())
