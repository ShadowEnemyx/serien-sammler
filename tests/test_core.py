import json
import shutil
from pathlib import Path

import pytest

from series_collector.core import (
    CONFIG_PATH,
    MANIFEST_NAME,
    CollectorError,
    classify_match,
    classify_path_match,
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


@pytest.fixture(autouse=True)
def fake_system_trash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep move-mode tests out of the real macOS Trash."""
    trash = tmp_path / "trash"
    trash.mkdir()

    def move_to_fake_trash(path: Path) -> None:
        destination = trash / path.name
        number = 2
        while destination.exists():
            destination = trash / f"{path.stem} ({number}){path.suffix}"
            number += 1
        shutil.move(str(path), str(destination))

    monkeypatch.setattr("series_collector.core.move_to_trash", move_to_fake_trash)
    return trash


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
    create_file(source / "nested" / "Ghost.Whisperer.S01E01.sample.mkv")
    create_file(source / "nested" / "Ghost.Whisperer.SAMPLE.srt")

    scan = scan_series("Ghost Whisperer", source, destination)

    assert scan.video_count == 1
    assert scan.subtitle_count == 2
    assert scan.new_count == 3
    assert scan.existing_count == 0


def test_scan_finds_all_episodes_when_series_name_is_only_in_folder(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    season = source / "Ghost.Whisperer" / "Staffel 1"
    for episode in range(1, 7):
        create_file(season / f"S01E{episode:02d}.mkv", bytes([episode]))
    create_file(season / "S01E01.srt", b"subtitle")
    create_file(source / "Other.Show" / "S01E01.mkv", b"other")

    scan = scan_series("Ghost Whisperer", source, destination)

    assert scan.video_count == 6
    assert scan.subtitle_count == 1
    assert sum(item.selected for item in scan.items) == 7
    assert {item.season for item in scan.items} == {1}
    assert classify_path_match(season / "S01E01.mkv", "Ghost Whisperer", source) == "exact"


def test_scan_finds_avi_episodes_and_sorts_sxxepxx_names(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    for episode in range(1, 5):
        create_file(
            source
            / "Drake.and.Josh.S04.COMPLETE"
            / f"Drake.and.Josh.S04EP{episode:02d}.avi",
            bytes([episode]),
        )

    scan = scan_series("Drake.and.Josh", source, destination)

    assert scan.video_count == 4
    assert sum(item.selected for item in scan.items) == 4
    assert {item.season for item in scan.items} == {4}
    assert {item.planned_destination.parent.name for item in scan.items} == {"S04"}


def test_sample_files_are_never_collected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    create_file(source / "Show.S01E01.mkv", b"episode")
    create_file(source / "Show.S01E01-Sample.mkv", b"short sample")
    create_file(source / "SAMPLE-Show-S01E01.srt", b"sample subtitle")

    scan = scan_series("Show", source, destination)
    summary = copy_series(scan)

    assert [item.source.name for item in scan.items] == ["Show.S01E01.mkv"]
    assert summary.copied == 1
    assert visible_files(destination / "Show") == ["S01/Show.S01E01.mkv"]


def test_copy_mode_keeps_source_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    episode = create_file(source / "Show.S01E01.mkv", b"episode")

    summary = copy_series(scan_series("Show", source, tmp_path / "destination"))

    assert summary.copied == 1
    assert summary.source_removed == 0
    assert episode.is_file()


def test_move_mode_moves_source_to_trash_only_after_verified_copy(tmp_path: Path, fake_system_trash: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    episode = create_file(source / "Show.S01E01.mkv", b"episode")

    summary = copy_series(scan_series("Show", source, destination, "move"))

    assert summary.copied == 1
    assert summary.source_removed == 1
    assert summary.source_folders_removed == 0
    assert summary.failed == 0
    assert not episode.exists()
    assert (fake_system_trash / episode.name).read_bytes() == b"episode"
    assert source.is_dir()
    assert (destination / "Show" / "S01" / episode.name).read_bytes() == b"episode"


def test_move_mode_moves_completed_parent_folder_and_leftovers_to_trash(
    tmp_path: Path, fake_system_trash: Path
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    release_folder = source / "Show.S01.COMPLETE"
    create_file(release_folder / "Show.S01E01.mkv", b"one")
    create_file(release_folder / "Show.S01E02.mkv", b"two")
    create_file(release_folder / "release-notes.txt", b"leftover")

    summary = copy_series(scan_series("Show", source, destination, "move"))

    assert summary.source_removed == 2
    assert summary.source_folders_removed == 1
    assert not release_folder.exists()
    assert (fake_system_trash / release_folder.name / "release-notes.txt").read_bytes() == b"leftover"
    assert source.is_dir()
    assert visible_files(destination / "Show") == [
        "S01/Show.S01E01.mkv",
        "S01/Show.S01E02.mkv",
    ]


def test_move_mode_moves_only_selected_file_to_trash_when_unselected_match_remains(
    tmp_path: Path, fake_system_trash: Path
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    release_folder = source / "release"
    selected = create_file(release_folder / "Show.S01E01.mkv", b"selected")
    ambiguous = create_file(release_folder / "ShowUS.S01E02.mkv", b"ambiguous")
    create_file(release_folder / "release-notes.txt", b"leftover")

    summary = copy_series(scan_series("Show", source, destination, "move"))

    assert not selected.exists()
    assert (fake_system_trash / selected.name).read_bytes() == b"selected"
    assert ambiguous.is_file()
    assert release_folder.is_dir()
    assert summary.source_folders_removed == 0


def test_move_mode_removes_source_when_identical_destination_exists(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    episode = create_file(source / "Show.S01E01.mkv", b"episode")
    existing = create_file(destination / "Show" / "S01" / episode.name, b"episode")

    scan = scan_series("Show", source, destination, "move")
    summary = copy_series(scan)

    assert sum(item.selected for item in scan.items) == 1
    assert summary.copied == 0
    assert summary.skipped == 0
    assert summary.source_removed == 1
    assert not episode.exists()
    assert existing.read_bytes() == b"episode"


def test_move_mode_ignores_and_preserves_sample_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    sample = create_file(source / "Show.S01E01.sample.mkv", b"sample")
    episode = create_file(source / "Show.S01E01.mkv", b"episode")

    summary = copy_series(scan_series("Show", source, tmp_path / "destination", "move"))

    assert summary.source_removed == 1
    assert sample.is_file()
    assert not episode.exists()


def test_move_mode_cancel_preserves_unprocessed_sources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    episodes = [
        create_file(source / f"Show.S01E0{number}.mkv", bytes([number]))
        for number in range(1, 4)
    ]
    cancelled = False

    def progress(_event: object) -> None:
        nonlocal cancelled
        cancelled = True

    summary = copy_series(
        scan_series("Show", source, destination, "move"),
        progress_callback=progress,
        cancel_requested=lambda: cancelled,
    )

    assert summary.cancelled is True
    assert summary.source_removed == 1
    assert not episodes[0].exists()
    assert episodes[1].exists()
    assert episodes[2].exists()


def test_move_mode_defers_folder_trash_when_cancelled_mid_release(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    release = source / "Show.S01.COMPLETE"
    episodes = [create_file(release / f"Show.S01E0{number}.mkv", bytes([number])) for number in range(1, 4)]
    cancelled = False

    def progress(_event: object) -> None:
        nonlocal cancelled
        cancelled = True

    summary = copy_series(
        scan_series("Show", source, destination, "move"),
        progress_callback=progress,
        cancel_requested=lambda: cancelled,
    )

    assert summary.cancelled is True
    assert summary.source_removed == 0
    assert all(episode.is_file() for episode in episodes)


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


def test_source_inside_series_destination_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    source = destination / "Show" / "incoming"
    create_file(source / "Show.S01E01.mkv")

    with pytest.raises(CollectorError) as caught:
        scan_series("Show", source, destination, "move")

    assert caught.value.code == "source_inside_destination"


def test_missing_source_and_empty_name_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CollectorError, match="series_required"):
        scan_series("", tmp_path, tmp_path / "destination")
    with pytest.raises(CollectorError, match="source_missing"):
        scan_series("Show", tmp_path / "missing", tmp_path / "destination")
    with pytest.raises(CollectorError, match="invalid_operation"):
        scan_series("Show", tmp_path, tmp_path / "destination", "delete")
