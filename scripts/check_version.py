"""Fail a release build when its tag does not match the application version."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from series_collector import __version__


tag = sys.argv[1] if len(sys.argv) > 1 else ""
expected = f"v{__version__}"
if tag != expected:
    raise SystemExit(f"Release tag {tag!r} does not match application version {expected!r}.")
print(f"Building Series Collector {__version__}")
