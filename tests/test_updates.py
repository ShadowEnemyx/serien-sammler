import json
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from series_collector.updates import (
    CHECKSUMS_NAME,
    RELEASE_DOWNLOAD_PREFIX,
    ReleaseAsset,
    UpdateError,
    UpdateInfo,
    check_for_updates,
    download_verified_update,
    prepare_self_update,
    update_asset_for_platform,
    update_check_due,
    version_tuple,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()

    def close(self) -> None:
        pass


class DownloadResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.position = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.position
        chunk = self.payload[self.position : self.position + size]
        self.position += len(chunk)
        return chunk

    def close(self) -> None:
        pass


def test_new_stable_release_is_detected() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        assert timeout == 5
        return FakeResponse(
            {
                "tag_name": "v1.2.0",
                "html_url": "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.2.0",
                "draft": False,
                "prerelease": False,
            }
        )

    info = check_for_updates(opener=opener, current_version="1.1.0")
    assert info.available is True
    assert info.latest_version == "1.2.0"


def test_invalid_or_prerelease_response_is_rejected() -> None:
    with pytest.raises(ValueError):
        check_for_updates(
            opener=lambda *_args, **_kwargs: FakeResponse(
                {"tag_name": "v2.0.0-beta", "html_url": "https://github.com/x", "prerelease": True}
            )
        )
    with pytest.raises(ValueError):
        version_tuple("not-a-version")
    assert version_tuple("1.1") == version_tuple("v1.1.0")


def test_update_interval() -> None:
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert update_check_due(None, now)
    assert not update_check_due((now - timedelta(hours=1)).isoformat(), now)
    assert update_check_due((now - timedelta(days=2)).isoformat(), now)


def test_platform_specific_update_asset_is_selected() -> None:
    info = UpdateInfo(
        "1.0.0",
        "1.1.0",
        "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.1.0",
        assets=(
            ReleaseAsset("Serien-Sammler-macOS-Apple-Silicon.zip", f"{RELEASE_DOWNLOAD_PREFIX}v1/a", 1),
            ReleaseAsset("Serien-Sammler-macOS-Intel.zip", f"{RELEASE_DOWNLOAD_PREFIX}v1/b", 1),
            ReleaseAsset("Serien-Sammler-Windows-x64.zip", f"{RELEASE_DOWNLOAD_PREFIX}v1/c", 1),
        ),
    )

    assert update_asset_for_platform(info, system="Darwin", machine="arm64").name.endswith("Apple-Silicon.zip")
    assert update_asset_for_platform(info, system="Darwin", machine="x86_64").name.endswith("Intel.zip")
    assert update_asset_for_platform(info, system="Windows", machine="AMD64").name.endswith("Windows-x64.zip")
    with pytest.raises(UpdateError):
        update_asset_for_platform(info, system="Linux", machine="x86_64")


def test_verified_update_download_uses_release_checksum(tmp_path: Path) -> None:
    asset_name = "Serien-Sammler-macOS-Apple-Silicon.zip"
    archive = b"verified update archive"
    checksum = f"{sha256(archive).hexdigest()}  {asset_name}\n".encode()
    info = UpdateInfo(
        "1.0.0",
        "1.1.0",
        "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.1.0",
        assets=(
            ReleaseAsset(asset_name, f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}", len(archive)),
            ReleaseAsset(CHECKSUMS_NAME, f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}", len(checksum)),
        ),
    )
    payloads = {
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}": archive,
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}": checksum,
    }

    downloaded = download_verified_update(
        info,
        tmp_path,
        opener=lambda request, timeout: DownloadResponse(payloads[request.full_url]),
        system="Darwin",
        machine="arm64",
    )

    assert downloaded.read_bytes() == archive


def test_update_download_with_wrong_checksum_is_removed(tmp_path: Path) -> None:
    asset_name = "Serien-Sammler-Windows-x64.zip"
    archive = b"update archive"
    checksum = f"{'0' * 64}  {asset_name}\n".encode()
    info = UpdateInfo(
        "1.0.0",
        "1.1.0",
        "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.1.0",
        assets=(
            ReleaseAsset(asset_name, f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}", len(archive)),
            ReleaseAsset(CHECKSUMS_NAME, f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}", len(checksum)),
        ),
    )
    payloads = {
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}": archive,
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}": checksum,
    }

    with pytest.raises(UpdateError, match="SHA-256"):
        download_verified_update(
            info,
            tmp_path,
            opener=lambda request, timeout: DownloadResponse(payloads[request.full_url]),
            system="Windows",
            machine="AMD64",
        )

    assert not (tmp_path / asset_name).exists()


def test_macos_update_prepares_a_launcher_without_replacing_the_running_app(tmp_path: Path) -> None:
    asset_name = "Serien-Sammler-macOS-Apple-Silicon.zip"
    archive_stream = BytesIO()
    with ZipFile(archive_stream, "w") as archive:
        archive.writestr("Serien-Sammler.app/Contents/MacOS/Serien-Sammler", b"new app")
    archive = archive_stream.getvalue()
    checksum = f"{sha256(archive).hexdigest()}  {asset_name}\n".encode()
    info = UpdateInfo(
        "1.0.0",
        "1.1.0",
        "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.1.0",
        assets=(
            ReleaseAsset(asset_name, f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}", len(archive)),
            ReleaseAsset(CHECKSUMS_NAME, f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}", len(checksum)),
        ),
    )
    payloads = {
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{asset_name}": archive,
        f"{RELEASE_DOWNLOAD_PREFIX}v1/{CHECKSUMS_NAME}": checksum,
    }
    executable = tmp_path / "Applications" / "Serien-Sammler.app" / "Contents" / "MacOS" / "Serien-Sammler"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"old app")

    prepared = prepare_self_update(
        info,
        opener=lambda request, timeout: DownloadResponse(payloads[request.full_url]),
        system="Darwin",
        machine="arm64",
        executable=executable,
    )

    assert prepared.launcher[0] == "/bin/sh"
    assert Path(prepared.launcher[1]).is_file()
    assert executable.read_bytes() == b"old app"
    assert "Serien-Sammler.app.previous" in Path(prepared.launcher[1]).read_text()
