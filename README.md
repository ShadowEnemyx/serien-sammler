# Series Collector

[Deutsche Anleitung](README.de.md)

Series Collector finds matching video and subtitle files in nested folders and safely collects them in one destination folder. Original files are copied, never moved or deleted.

## Download

Download the latest ready-to-run version from [GitHub Releases](https://github.com/ShadowEnemyx/serien-sammler/releases/latest). Python is not required.

- **Windows installer:** `Serien-Sammler-Windows-x64-Setup.exe`
- **Windows portable:** `Serien-Sammler-Windows-x64.zip`
- **Apple Silicon Mac:** `Serien-Sammler-macOS-Apple-Silicon.dmg` or the matching ZIP
- **Intel Mac:** `Serien-Sammler-macOS-Intel.dmg` or the matching ZIP

Builds are signed automatically when the repository owner has configured signing certificates. `BUILD-STATUS.txt` inside each package states whether that build is signed. For an unsigned Windows build, SmartScreen may require **More info → Run anyway**. For an unsigned macOS build, right-click the app, select **Open**, then confirm **Open**. Download only from this repository and use `SHA256SUMS.txt` to verify files when needed.

## Features

- German and English interface with automatic language detection
- Recursive search through all subfolders
- Flexible matching: `Ghost Whisperer` also finds `Ghost.Whisperer`, `Ghost-Whisperer`, and `GhostWhisperer`
- Exact, likely, and ambiguous match classification; ambiguous results require manual selection
- Selectable preview with source path and planned copy, skip, or rename action
- Content fingerprints prevent duplicate copies even when source paths or filenames differ
- Different files with the same name are kept as ` (2)`, ` (3)`, and so on
- Verified temporary copies, progress display, and safe cancellation between files
- Optional daily update notification plus manual update check
- Local rotating logs and an exportable diagnostic report; no telemetry
- Supports `.mkv`, `.mp4`, `.srt`, `.ass`, `.ssa`, `.vtt`, and `.sub`

The destination folder must not be inside the source folder. Existing version 1 manifests and configuration files are migrated automatically.

## Command line

Python 3.9 or newer is required when running from source.

```bash
python3 serien_sammler.py \
  --source "/path/to/download-folder" \
  --destination "/path/to/videos-folder" \
  --series "Ghost Whisperer" \
  --language en \
  --preview
```

Remove `--preview` to copy. Optional switches include `--remember-folders`, `--include-ambiguous`, `--check-updates`, and `--log-file /path/to/log.txt`. The `.command`, `.bat`, and PowerShell launchers remain source-code fallbacks.

## Development and releases

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

PyInstaller and Pillow are pinned in `requirements-build.txt`. Tags such as `v1.1.0` test and build Windows x64, macOS Apple Silicon, and macOS Intel artifacts, exercise the installer/DMGs, create SHA-256 checksums, and publish a release.

Optional GitHub Actions secrets enable official signing:

- Windows: `WINDOWS_CERTIFICATE_BASE64`, `WINDOWS_CERTIFICATE_PASSWORD`
- Apple: `APPLE_CERTIFICATE_BASE64`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD`

Without these secrets, the same workflow intentionally publishes clearly marked unsigned builds. Apple distribution certificates require an Apple Developer membership; a trusted Windows code-signing certificate must be obtained separately.

## Privacy and license

Update checks contact only GitHub's public Releases API and can be disabled. Logs remain on the local computer. This project is licensed under the [MIT License](LICENSE).
