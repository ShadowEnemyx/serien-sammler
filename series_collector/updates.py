"""Small dependency-free GitHub Releases update client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from urllib.request import Request, urlopen

from series_collector import __version__


RELEASE_API = "https://api.github.com/repos/ShadowEnemyx/serien-sammler/releases/latest"
CHECK_INTERVAL = timedelta(hours=24)


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str

    @property
    def available(self) -> bool:
        return version_tuple(self.latest_version) > version_tuple(self.current_version)


def version_tuple(value: str) -> tuple[int, ...]:
    cleaned = value.strip().removeprefix("v")
    parts = cleaned.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Invalid version: {value}")
    numbers = tuple(int(part) for part in parts)
    return numbers + (0,) * max(0, 3 - len(numbers))


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
    return UpdateInfo(current_version=current_version, latest_version=tag.removeprefix("v"), release_url=url)


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
