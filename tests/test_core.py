import json
from pathlib import Path

import pytest

from series_collector.core import (
    CONFIG_PATH,
    MANIFEST_NAME,
    CollectorError,
    classify_match,
    copy_series,
    default_language,
    detect_season,
    folder_name,
    load_config,
    normalise_for_search,
    normalise_language,
    save_config,
    scan_series,
)


def create_file(path: Path, content: bytes = b"content") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def visible_files(folder: Path) -> list[str]:
    return sorted(
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(folder).parts)
    )


def test_name_normalisation_ignores_separators() -> None:
    assert normalise_for_search("Ghost Whisperer") == "ghostwhisperer"
    assert normalise_for_search("Ghost.Whisperer-S01") == "ghostwhisperers01"
    assert folder_name(" Ghost/Whisperer. ") == "Ghost Whisperer"
    assert classify_match("GhostWhispererS01E01.mkv", "Ghost Whisperer") == "exact"
    assert classify_match("Ghost.Whisperer.Special.mkv", "Ghost Whisperer") == "likely"
    assert classify_match("TheOfficeUS.S01E01.mkv", "The Office") == "ambiguous"
    assert detect_season("Ghost.Whisperer.S01E03.mkv") == 1
    assert detect_season("Ghost Whisperer Staffel 2 Folge 4.mkv") == 2
    assert detect_season("Ghost Whisperer Season-03 Episode 2.mkv") == 3
    assert detect_season("GhostWhisperer.4x05.mp4") == 4
    assert detect_season("GhostWhispererS05E03.mkv") == 5
    assert detect_season("Ghost Whisperer Special.mkv") is None


def test_language_defaults_and_validation() -> None:
    assert default_language() in {"de", "en"}
    assert normalise_language("de") == "de"
    assert normalise_language("en") == "en"
    assert normalise_language("invalid") in {"de", "en"}


def test_scan_finds_videos_and_subtitles(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "nested" / "Ghost.Whisperer.S01E01.mkv")
    create_file(source / "nested" / "GhostWhispererS01E01.srt")
    create_file(source / "nested" / "Ghost-Whisperer-S01E02.ass")
    create_file(source / "nested" / "Other.Show.S01E01.mp4")
    create_file(source / "nested" / "._Ghost.Whisperer.S01E01.mkv")

    scan = scan_series("Ghost Whisperer", source, destination)

    assert scan.video_count == 1
    assert scan.subtitle_count == 2
    assert scan.new_count == 3
    assert scan.existing_count == 0


def test_repeat_run_skips_known_files_and_adds_new_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "one" / "Show.S01E01.mkv", b"first")
    create_file(source / "two" / "Show.S01E01.mkv", b"second source")

    first_scan = scan_series("Show", source, destination)
    first_summary = copy_series(first_scan)
    target = destination / "Show"

    assert first_summary.copied == 2
    assert visible_files(target) == ["S01/Show.S01E01 (2).mkv", "S01/Show.S01E01.mkv"]
    assert (target / MANIFEST_NAME).is_file()

    second_scan = scan_series("Show", source, destination)
    second_summary = copy_series(second_scan)
    assert second_scan.existing_count == 2
    assert second_summary.copied == 0
    assert second_summary.processed == 0
    assert second_summary.skipped == 0
    assert visible_files(target) == ["S01/Show.S01E01 (2).mkv", "S01/Show.S01E01.mkv"]

    create_file(source / "three" / "Show.S01E01.mkv", b"third source")
    third_scan = scan_series("Show", source, destination)
    third_summary = copy_series(third_scan)
    assert third_scan.new_count == 1
    assert third_summary.copied == 1
    assert visible_files(target) == [
        "S01/Show.S01E01 (2).mkv",
        "S01/Show.S01E01 (3).mkv",
        "S01/Show.S01E01.mkv",
    ]


def test_cancel_stops_between_files_and_preserves_progress(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    for episode in range(1, 4):
        create_file(source / f"Show.S01E0{episode}.mkv", bytes([episode]))

    scan = scan_series("Show", source, destination)
    cancelled = False

    def progress(_event: object) -> None:
        nonlocal cancelled
        cancelled = True

    summary = copy_series(scan, progress_callback=progress, cancel_requested=lambda: cancelled)

    assert summary.cancelled is True
    assert summary.processed == 1
    assert summary.copied == 1
    rescan = scan_series("Show", source, destination)
    assert rescan.existing_count == 1
    assert rescan.new_count == 2


def test_configuration_migration_and_language(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"source": "/old/source", "destination": "/old/destination"}))

    assert load_config(config_path) == {"source": "/old/source", "destination": "/old/destination"}
    save_config(language="en", config_path=config_path)

    assert load_config(config_path) == {
        "source": "/old/source",
        "destination": "/old/destination",
        "language": "en",
    }
    save_config(check_updates=False, last_update_check="2026-01-01T00:00:00+00:00", config_path=config_path)
    assert load_config(config_path)["check_updates"] is False


def test_ambiguous_matches_are_visible_but_not_selected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "TheOfficeUS.S01E01.mkv", b"us")
    create_file(source / "TheOfficeS01E01.mkv", b"original")

    scan = scan_series("The Office", source, destination)

    assert scan.ambiguous_count == 1
    assert sum(item.selected for item in scan.items) == 1
    assert {item.match_quality for item in scan.items} == {"exact", "ambiguous"}


def test_identical_content_from_different_sources_is_copied_once(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "a" / "Show.S01E01.mkv", b"same episode")
    create_file(source / "b" / "Show.S01E01-copy.mkv", b"same episode")

    scan = scan_series("Show", source, destination)
    summary = copy_series(scan)

    assert scan.new_count == 1
    assert scan.existing_count == 1
    assert summary.copied == 1
    assert visible_files(destination / "Show") == ["S01/Show.S01E01.mkv"]


def test_orphan_destination_is_adopted_by_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "Show.S01E01.mkv", b"episode")
    target = destination / "Show"
    create_file(target / "renamed.mkv", b"episode")

    scan = scan_series("Show", source, destination)
    summary = copy_series(scan)

    assert scan.existing_count == 0
    assert scan.move_count == 1
    assert summary.moved == 1
    assert visible_files(target) == ["S01/renamed.mkv"]
    manifest = json.loads((target / MANIFEST_NAME).read_text())
    assert manifest["schema_version"] == 2


def test_different_files_with_same_name_are_renamed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "a" / "Show.S01E01.mkv", b"first")
    create_file(source / "b" / "Show.S01E01.mkv", b"second")

    scan = scan_series("Show", source, destination)
    assert {item.destination_action for item in scan.items} == {"action_copy", "action_rename"}
    copy_series(scan)
    assert visible_files(destination / "Show") == [
        "S01/Show.S01E01 (2).mkv",
        "S01/Show.S01E01.mkv",
    ]


def test_changed_source_after_preview_fails_safely(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    episode = create_file(source / "Show.S01E01.mkv", b"first")
    scan = scan_series("Show", source, destination)
    episode.write_bytes(b"changed")

    summary = copy_series(scan)

    assert summary.failed == 1
    assert visible_files(destination / "Show") == []


def test_corrupt_manifest_is_backed_up_on_copy(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "Show.S01E01.mkv", b"episode")
    target = destination / "Show"
    target.mkdir(parents=True)
    (target / MANIFEST_NAME).write_text("{broken")

    copy_series(scan_series("Show", source, destination))

    assert json.loads((target / MANIFEST_NAME).read_text())["schema_version"] == 2
    assert len(list(target.glob(f"{MANIFEST_NAME}.corrupt-*"))) == 1


def test_version_one_manifest_is_migrated_lazily(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    episode = create_file(source / "Show.S01E01.mkv", b"episode")
    target = destination / "Show"
    copied = create_file(target / "Show.S01E01.mkv", b"episode")
    stats = episode.stat()
    (target / MANIFEST_NAME).write_text(
        json.dumps(
            {
                "files": {
                    str(episode.resolve()): {
                        "source": str(episode.resolve()),
                        "size": stats.st_size,
                        "modified": stats.st_mtime_ns,
                        "destination": copied.name,
                    }
                }
            }
        )
    )

    summary = copy_series(scan_series("Show", source, destination))

    assert summary.moved == 1
    assert visible_files(target) == ["S01/Show.S01E01.mkv"]
    assert json.loads((target / MANIFEST_NAME).read_text())["schema_version"] == 2


def test_episodes_and_subtitles_are_sorted_into_season_folders(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "Ghost.Whisperer.S01E01.mkv", b"s1")
    create_file(source / "Ghost Whisperer Staffel 2 Folge 1.mkv", b"s2")
    create_file(source / "Ghost Whisperer Season 3 Episode 1.srt", b"s3 subtitle")
    create_file(source / "Ghost Whisperer.4x05.mp4", b"s4")
    create_file(source / "Ghost Whisperer Special.mkv", b"special")

    scan = scan_series("Ghost Whisperer", source, destination)
    summary = copy_series(scan)

    assert summary.copied == 5
    assert visible_files(destination / "Ghost Whisperer") == [
        "Ghost Whisperer Special.mkv",
        "S01/Ghost.Whisperer.S01E01.mkv",
        "S02/Ghost Whisperer Staffel 2 Folge 1.mkv",
        "S03/Ghost Whisperer Season 3 Episode 1.srt",
        "S04/Ghost Whisperer.4x05.mp4",
    ]


def test_destination_inside_source_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    create_file(source / "Show.S01E01.mkv")

    with pytest.raises(CollectorError) as caught:
        scan_series("Show", source, source / "collected")

    assert caught.value.code == "destination_inside_source"


def test_missing_source_and_empty_name_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CollectorError, match="series_required"):
        scan_series("", tmp_path, tmp_path / "destination")
    with pytest.raises(CollectorError, match="source_missing"):
        scan_series("Show", tmp_path / "missing", tmp_path / "destination")
