# Series Collector

[Deutsche Anleitung](README.de.md)

A small macOS app that collects episodes of a TV series from many subfolders into one folder.

Original files are only **copied** — never moved or deleted.

## Usage on macOS

1. Double-click `Serien-Sammler.command`. On the first launch, macOS may require right-clicking it and choosing **Open**.
2. Select the folder that should be searched. All of its subfolders are searched as well.
3. Select the destination folder, for example a folder named `Movies`.
4. Enter the name of the series, for example `Ghost Whisperer`.
5. The app creates a folder named `Ghost Whisperer` in the destination folder, copies all matching `.mkv` and `.mp4` files into it, then opens that folder in Finder.

The search ignores differences in periods, commas, spaces, and hyphens. Searching for `Ghost Whisperer` therefore also finds files named `Ghost.Whisperer...`, `Ghost-Whisperer...`, and `GhostWhisperer...`. macOS metadata files starting with `._` are skipped. Existing files are never overwritten; ` (2)`, ` (3)`, and so on are added to duplicate names.

## Usage on Windows

1. Install Python 3 from [python.org](https://www.python.org/downloads/windows/). During setup, enable **Add Python to PATH**.
2. Double-click `Serien-Sammler.bat`.
3. Select the source folder, destination folder, and enter the series name.

The finished series folder opens automatically in Windows Explorer.

## Terminal usage

```bash
/usr/bin/python3 serien_sammler.py \
  --source "/path/to/download-folder" \
  --destination "/path/to/movies-folder" \
  --series "Ghost Whisperer"
```

## License

This project is licensed under the [MIT License](LICENSE). You may use, modify, and redistribute it as long as the license notice is retained.
