#!/usr/bin/env python3
"""Sammelt Folgen einer Serie für HandBrake in einem einzigen Ordner."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


VIDEO_ENDUNGEN = {".mkv", ".mp4"}


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


def matching_videos(source: Path, keyword: str) -> list[Path]:
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not path.name.startswith("._")
        and path.suffix.casefold() in VIDEO_ENDUNGEN
        and keyword in normalise_for_search(path.name)
    )


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
    copied = 0
    errors: list[str] = []
    for number, file in enumerate(files, start=1):
        print(f"Kopiere {number} von {len(files)}: {file.name}")
        try:
            shutil.copy2(file, free_name(target, file.name))
            copied += 1
        except OSError as error:
            errors.append(f"{file.name}: {error}")

    if copied:
        print(f"\nFertig: {copied} Datei(en) liegen jetzt in: {target}")
        subprocess.run(["open", str(target)], check=False)
    if errors:
        print(f"\n{len(errors)} Datei(en) konnten nicht kopiert werden:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sammelt Serienfolgen für HandBrake.")
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
