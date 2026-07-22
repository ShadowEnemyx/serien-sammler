from pathlib import Path

from series_collector.logging_utils import configure_logging, save_diagnostic_report


def test_custom_log_and_diagnostic_report(tmp_path: Path) -> None:
    log_path = configure_logging(tmp_path / "logs" / "custom.log")
    report = tmp_path / "diagnostic.txt"
    save_diagnostic_report(report, log_path)

    assert log_path.is_file()
    text = report.read_text()
    assert "Telemetry: disabled" in text
    assert "Version: " in text
