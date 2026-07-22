from pathlib import Path

from series_collector import __version__
from series_collector.cli import main
from series_collector.updates import UpdateInfo


def test_version(capsys: object) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_preview_in_english(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    (source / "Show.S01E01.mkv").write_bytes(b"video")
    (source / "Show.S01E01.srt").write_text("subtitle")

    result = main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--series",
            "Show",
            "--language",
            "en",
            "--preview",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "Found: 1 video(s) and 1 subtitle file(s)" in output
    assert "New to copy: 2" in output


def test_preview_in_german(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    (source / "Serie.S01E01.mp4").write_bytes(b"video")

    result = main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--series",
            "Serie",
            "--language",
            "de",
            "--preview",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "Gefunden: 1 Video(s)" in output
    assert "Neu zu kopieren: 1" in output


def test_no_matches_returns_one(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()

    result = main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--series",
            "Missing",
            "--preview",
            "--language",
            "en",
        ]
    )

    assert result == 1
    assert "No matching" in capsys.readouterr().out


def test_cli_update_check(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(
        "series_collector.cli.check_for_updates",
        lambda: UpdateInfo("1.1.0", "1.2.0", "https://github.com/ShadowEnemyx/serien-sammler/releases/tag/v1.2.0"),
    )

    assert main(["--check-updates", "--language", "en"]) == 0
    assert "Version 1.2.0 is available" in capsys.readouterr().out
