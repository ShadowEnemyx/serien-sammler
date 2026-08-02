from pathlib import Path
from subprocess import CompletedProcess

from series_collector.trash import _macos_trash


def test_macos_trash_resolves_the_complete_path_as_an_alias(monkeypatch: object, tmp_path: Path) -> None:
    source = tmp_path / "Tomb.Raider.King.S01E01.mkv"
    source.write_bytes(b"episode")
    captured: list[object] = []

    def fake_run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        captured.extend(args[0])
        return CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr("series_collector.trash.subprocess.run", fake_run)
    _macos_trash(source)

    script = captured[2]
    assert "POSIX file (item 1 of argv) as alias" in script
    assert captured[3] == str(source)
