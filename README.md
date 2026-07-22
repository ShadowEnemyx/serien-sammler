# Series Collector

[Deutsche Anleitung](README.de.md)

A small macOS and Windows app that collects episodes of a TV series and their matching subtitle files from many subfolders into one folder.

Original files are only **copied** — never moved or deleted.

## Usage on macOS

1. Double-click `Serien-Sammler.command`. On the first launch, macOS may require right-clicking it and choosing **Open**.
2. On the first run, select the folder to search and the destination folder. These folders are remembered; later runs let you reuse or change them.
3. Enter the name of the series, for example `Ghost Whisperer`.
4. Review the preview showing found, new, and already copied files, then confirm the copy.
5. The app creates a folder named `Ghost Whisperer` in the destination folder, copies the new matching files into it, then opens that folder in Finder.

Supported video formats are `.mkv` and `.mp4`. Matching subtitles in `.srt`, `.ass`, `.ssa`, `.vtt`, and `.sub` format are collected as well.

The search ignores differences in periods, commas, spaces, and hyphens. Searching for `Ghost Whisperer` therefore also finds files named `Ghost.Whisperer...`, `Ghost-Whisperer...`, and `GhostWhisperer...`. macOS metadata files starting with `._` are skipped. The app remembers copied source files in a hidden file inside the series folder, so a later run only adds new episodes and subtitles. Existing files are never overwritten; ` (2)`, ` (3)`, and so on are added to different source files with the same name.

## Usage on Windows

1. Install Python 3 from [python.org](https://www.python.org/downloads/windows/). During setup, enable **Add Python to PATH**.
2. Double-click `Serien-Sammler.bat`.
3. On the first run, select the source folder and destination folder. Later runs let you reuse or change them.
4. Enter the series name, review the preview, and confirm the copy.

The finished series folder opens automatically in Windows Explorer.

## Terminal usage

```bash
/usr/bin/python3 serien_sammler.py \
  --source "/path/to/download-folder" \
  --destination "/path/to/movies-folder" \
  --series "Ghost Whisperer" \
  --remember-folders
```

Add `--preview` to show the planned changes without copying anything. After folders have been remembered, `--source` and `--destination` can be omitted.

## License

This project is licensed under the [MIT License](LICENSE). You may use, modify, and redistribute it as long as the license notice is retained.
