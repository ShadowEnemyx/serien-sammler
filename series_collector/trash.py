"""Move files to the operating system's Trash without extra dependencies."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


class TrashError(OSError):
    """The operating system could not put a path into its Trash."""


def _macos_trash(path: Path) -> None:
    script = """on run argv
tell application \"Finder\" to delete POSIX file (item 1 of argv)
end run"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script, str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise TrashError(f"could not open the macOS Trash: {error}") from error
    if result.returncode:
        message = result.stderr.strip() or "Finder could not move the item to the Trash"
        raise TrashError(message)


def _windows_trash(path: Path) -> None:
    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("wFunc", ctypes.c_uint),
            ("pFrom", ctypes.c_wchar_p),
            ("pTo", ctypes.c_wchar_p),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", ctypes.c_bool),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", ctypes.c_wchar_p),
        ]

    # Values from the Windows Shell API. FOF_ALLOWUNDO sends the item to the
    # Recycle Bin instead of deleting it permanently.
    FO_DELETE = 3
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040
    FOF_NOERRORUI = 0x0400
    operation = SHFILEOPSTRUCTW()
    operation.wFunc = FO_DELETE
    operation.pFrom = str(path.resolve()) + "\0\0"
    operation.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if result or operation.fAnyOperationsAborted:
        raise TrashError(f"Windows could not move the item to the Recycle Bin (code {result})")


def _free_destination(folder: Path, name: str) -> Path:
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


def _freedesktop_trash(path: Path) -> None:
    """Use the standard Linux Trash layout as a dependency-free fallback."""
    trash_root = Path.home() / ".local" / "share" / "Trash"
    files_folder = trash_root / "files"
    info_folder = trash_root / "info"
    try:
        files_folder.mkdir(parents=True, exist_ok=True)
        info_folder.mkdir(parents=True, exist_ok=True)
        destination = _free_destination(files_folder, path.name)
        info_path = info_folder / f"{destination.name}.trashinfo"
        original = quote(str(path.resolve()))
        deletion_date = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S")
        info_path.write_text(
            f"[Trash Info]\nPath={original}\nDeletionDate={deletion_date}\n", encoding="utf-8"
        )
        shutil.move(str(path), str(destination))
    except OSError as error:
        raise TrashError(f"could not move the item to the Trash: {error}") from error


def move_to_trash(path: Path) -> None:
    """Move *path* to the platform's Trash / Recycle Bin.

    The caller must only use this after a verified destination copy exists.
    """
    if not path.exists():
        raise TrashError(f"source item no longer exists: {path}")
    if sys.platform == "darwin":
        _macos_trash(path)
    elif os.name == "nt":
        _windows_trash(path)
    else:
        _freedesktop_trash(path)
