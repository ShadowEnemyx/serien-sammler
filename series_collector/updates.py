"""GitHub Releases update checks, verified downloads, and self-update helpers."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from series_collector import __version__


REPOSITORY = "ShadowEnemyx/serien-sammler"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASE_DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
CHECKSUMS_NAME = "SHA256SUMS.txt"
CHECK_INTERVAL = timedelta(hours=24)
CHUNK_SIZE = 1024 * 1024


class UpdateError(Exception):
    """Raised when a release cannot be safely downloaded or installed."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str
    assets: tuple[ReleaseAsset, ...] = ()

    @property
    def available(self) -> bool:
        return version_tuple(self.latest_version) > version_tuple(self.current_version)


@dataclass(frozen=True)
class PreparedUpdate:
    version: str
    staging_dir: Path
    launcher: tuple[str, ...]


def version_tuple(value: str) -> tuple[int, ...]:
    cleaned = value.strip().removeprefix("v")
    parts = cleaned.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Invalid version: {value}")
    numbers = tuple(int(part) for part in parts)
    return numbers + (0,) * max(0, 3 - len(numbers))


def _release_asset(value: object) -> Optional[ReleaseAsset]:
    if not isinstance(value, dict):
        return None
    name = value.get("name")
    download_url = value.get("browser_download_url")
    size = value.get("size")
    if (
        not isinstance(name, str)
        or not isinstance(download_url, str)
        or not download_url.startswith(RELEASE_DOWNLOAD_PREFIX)
        or not isinstance(size, int)
        or size < 0
    ):
        return None
    return ReleaseAsset(name=name, download_url=download_url, size=size)


def check_for_updates(
    opener: Callable[..., object] = urlopen,
    current_version: str = __version__,
) -> UpdateInfo:
    request = Request(
        RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"Serien-Sammler/{current_version}"},
    )
    response = opener(request, timeout=5)
    try:
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    if payload.get("draft") or payload.get("prerelease"):
        raise ValueError("Latest release is not stable")
    tag = payload.get("tag_name")
    url = payload.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str) or not url.startswith("https://github.com/"):
        raise ValueError("Invalid GitHub release response")
    version_tuple(tag)
    raw_assets = payload.get("assets", [])
    assets = tuple(
        asset for value in raw_assets if (asset := _release_asset(value)) is not None
    ) if isinstance(raw_assets, list) else ()
    return UpdateInfo(
        current_version=current_version,
        latest_version=tag.removeprefix("v"),
        release_url=url,
        assets=assets,
    )


def update_asset_for_platform(
    info: UpdateInfo,
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> ReleaseAsset:
    current_system = (system or platform.system()).casefold()
    current_machine = (machine or platform.machine()).casefold()
    if current_system == "darwin":
        name = (
            "Serien-Sammler-macOS-Apple-Silicon.zip"
            if current_machine in {"arm64", "aarch64"}
            else "Serien-Sammler-macOS-Intel.zip"
            if current_machine in {"x86_64", "amd64"}
            else ""
        )
    elif current_system == "windows" and current_machine in {"x86_64", "amd64"}:
        name = "Serien-Sammler-Windows-x64.zip"
    else:
        name = ""
    asset = next((candidate for candidate in info.assets if candidate.name == name), None)
    if asset is None:
        raise UpdateError("No compatible update download is available for this computer.")
    return asset


def _asset(info: UpdateInfo, name: str) -> ReleaseAsset:
    asset = next((candidate for candidate in info.assets if candidate.name == name), None)
    if asset is None:
        raise UpdateError("The release does not include the required checksum file.")
    return asset


def _download(asset: ReleaseAsset, destination: Path, opener: Callable[..., object], progress: Optional[Callable[[int, int], None]]) -> str:
    request = Request(
        asset.download_url,
        headers={"Accept": "application/octet-stream", "User-Agent": f"Serien-Sammler/{__version__}"},
    )
    response = opener(request, timeout=30)
    temporary = destination.with_name(f".{destination.name}.part")
    digest = hashlib.sha256()
    received = 0
    try:
        with temporary.open("wb") as output:
            while chunk := response.read(CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if progress:
                    progress(received, asset.size)
        if asset.size and received != asset.size:
            raise UpdateError(f"Download size for {asset.name} did not match the release.")
        temporary.replace(destination)
        return digest.hexdigest()
    except Exception:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def _expected_checksum(checksum_file: Path, filename: str) -> str:
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1].lstrip(" *") == filename:
            digest = parts[0].casefold()
            if len(digest) == 64 and all(character in "0123456789abcdef" for character in digest):
                return digest
    raise UpdateError(f"No SHA-256 checksum was found for {filename}.")


def download_verified_update(
    info: UpdateInfo,
    staging_dir: Path,
    opener: Callable[..., object] = urlopen,
    progress: Optional[Callable[[int, int], None]] = None,
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> Path:
    asset = update_asset_for_platform(info, system=system, machine=machine)
    staging_dir.mkdir(parents=True, exist_ok=True)
    checksums = staging_dir / CHECKSUMS_NAME
    _download(_asset(info, CHECKSUMS_NAME), checksums, opener, None)
    destination = staging_dir / asset.name
    received_checksum = _download(asset, destination, opener, progress)
    if received_checksum != _expected_checksum(checksums, asset.name):
        destination.unlink(missing_ok=True)
        raise UpdateError("The downloaded update did not match its SHA-256 checksum.")
    return destination


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as package:
        target_root = destination.resolve()
        for member in package.infolist():
            member_path = (destination / member.filename).resolve()
            if not member_path.is_relative_to(target_root) or stat.S_ISLNK(member.external_attr >> 16):
                raise UpdateError("The update archive contains an unsafe file path.")
        package.extractall(destination)


def _macos_app(executable: Path) -> Optional[Path]:
    for parent in executable.resolve().parents:
        if parent.name == "Serien-Sammler.app" and parent.suffix == ".app":
            return parent
    return None


def _write_macos_launcher(staging_dir: Path, replacement: Path, current_app: Path) -> Path:
    launcher = staging_dir / "install-update.sh"
    backup = current_app.with_name(f"{current_app.name}.previous")
    script = "\n".join(
        (
            "#!/bin/sh",
            "set -eu",
            "sleep 2",
            f"rm -rf {shlex.quote(str(backup))}",
            f"mv {shlex.quote(str(current_app))} {shlex.quote(str(backup))}",
            f"mv {shlex.quote(str(replacement))} {shlex.quote(str(current_app))}",
            f"open {shlex.quote(str(current_app))}",
            f"rm -rf {shlex.quote(str(backup))}",
            f"rm -rf {shlex.quote(str(staging_dir))}",
            "",
        )
    )
    launcher.write_text(script, encoding="utf-8")
    launcher.chmod(0o700)
    return launcher


def _write_windows_launcher(staging_dir: Path, replacement: Path, current_executable: Path) -> Path:
    launcher = staging_dir / "install-update.cmd"
    script = "\r\n".join(
        (
            "@echo off",
            "timeout /t 2 /nobreak >nul",
            f'copy /Y "{replacement}" "{current_executable}" >nul',
            f'start "" "{current_executable}"',
            f'del "{staging_dir / "update.zip"}" 2>nul',
            f'rmdir /S /Q "{staging_dir / "extracted"}" 2>nul',
            "del \"%~f0\"",
            "",
        )
    )
    launcher.write_text(script, encoding="utf-8")
    return launcher


def prepare_self_update(
    info: UpdateInfo,
    opener: Callable[..., object] = urlopen,
    progress: Optional[Callable[[int, int], None]] = None,
    system: Optional[str] = None,
    machine: Optional[str] = None,
    executable: Optional[Path] = None,
) -> PreparedUpdate:
    current_system = (system or platform.system()).casefold()
    if current_system not in {"darwin", "windows"}:
        raise UpdateError("Automatic installation is not available on this operating system.")
    if not getattr(sys, "frozen", False) and executable is None:
        raise UpdateError("Automatic installation is available only in the downloaded app.")

    staging_dir = Path(tempfile.mkdtemp(prefix="serien-sammler-update-"))
    try:
        archive = download_verified_update(
            info, staging_dir, opener=opener, progress=progress, system=system, machine=machine
        )
        extracted = staging_dir / "extracted"
        _safe_extract_zip(archive, extracted)
        executable_path = (executable or Path(sys.executable)).resolve()

        if current_system == "darwin":
            current_app = _macos_app(executable_path)
            replacement = extracted / "Serien-Sammler.app"
            if current_app is None or not replacement.is_dir() or not os.access(current_app.parent, os.W_OK):
                raise UpdateError("The app must be in a writable folder to install this update automatically.")
            launcher = _write_macos_launcher(staging_dir, replacement, current_app)
            command = ("/bin/sh", str(launcher))
        else:
            replacement = extracted / "Serien-Sammler.exe"
            if executable_path.name != "Serien-Sammler.exe" or not replacement.is_file() or not os.access(
                executable_path.parent, os.W_OK
            ):
                raise UpdateError("The app must be in a writable folder to install this update automatically.")
            launcher = _write_windows_launcher(staging_dir, replacement, executable_path)
            command = ("cmd.exe", "/c", str(launcher))
        return PreparedUpdate(version=info.latest_version, staging_dir=staging_dir, launcher=command)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def start_prepared_update(update: PreparedUpdate) -> None:
    subprocess.Popen(update.launcher, close_fds=True)


def discard_prepared_update(update: PreparedUpdate) -> None:
    shutil.rmtree(update.staging_dir, ignore_errors=True)


def update_check_due(last_check: Optional[str], now: Optional[datetime] = None) -> bool:
    if not last_check:
        return True
    try:
        previous = datetime.fromisoformat(last_check)
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    current = now or datetime.now(timezone.utc)
    return current - previous >= CHECK_INTERVAL
