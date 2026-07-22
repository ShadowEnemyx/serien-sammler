# Series Collector

[Deutsche Anleitung](README.de.md)

Series Collector finds matching video and subtitle files in nested folders and copies only new files into a single series folder.

## Download

Download the latest ready-to-run version from [GitHub Releases](https://github.com/ShadowEnemyx/serien-sammler/releases/latest). Python is not required.

- **Windows:** Download `Serien-Sammler-Windows-x64.zip`, extract it, and start `Serien-Sammler.exe`.
- **Apple Silicon Mac:** Download `Serien-Sammler-macOS-Apple-Silicon.zip`, extract it, and open `Serien-Sammler.app`.
- **Intel Mac:** Download `Serien-Sammler-macOS-Intel.zip`, extract it, and open `Serien-Sammler.app`.

The first release is unsigned. Windows SmartScreen may require **More info → Run anyway**. On macOS, right-click the app, select **Open**, then confirm **Open**. Only download releases from this repository and compare the provided `SHA256SUMS.txt` if you want to verify the archive.

## Features

- German and English interface with automatic language detection
- Recursive search through all subfolders
- Flexible matching: `Ghost Whisperer` also finds `Ghost.Whisperer`, `Ghost-Whisperer`, and `GhostWhisperer`
- Preview showing videos, subtitles, new files, and existing files
- Progress display and safe cancellation between files
- Remembers source folder, destination folder, and language
- Adds only new files on later runs
- Never overwrites existing files
- Supports `.mkv`, `.mp4`, `.srt`, `.ass`, `.ssa`, `.vtt`, and `.sub`

Original files are only **copied** — never moved or deleted. The destination folder must not be inside the source folder.

## Use from source

Python 3.9 or newer is required when running from source.

```bash
python3 serien_sammler.py \
  --source "/path/to/download-folder" \
  --destination "/path/to/videos-folder" \
  --series "Ghost Whisperer" \
  --language en \
  --preview
```

Remove `--preview` to copy files. Add `--remember-folders` to save the selected folders. The existing `.command` and `.bat` launchers remain available as source-code fallbacks.

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

PyInstaller is pinned in `requirements-build.txt`. Version tags such as `v1.0.0` automatically run all tests and publish Windows x64, macOS Apple Silicon, and macOS Intel downloads.

## License

This project is licensed under the [MIT License](LICENSE).
