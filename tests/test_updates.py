import json
from datetime import datetime, timedelta, timezone

import pytest

from series_collector.updates import check_for_updates, update_check_due, version_tuple


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()

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
