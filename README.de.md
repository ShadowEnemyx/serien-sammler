# Serien-Sammler

[English README](README.md)

Der Serien-Sammler findet passende Video- und Untertiteldateien in verschachtelten Ordnern und kopiert nur neue Dateien in einen gemeinsamen Serienordner.

## Download

Die aktuelle fertige Version gibt es unter [GitHub Releases](https://github.com/ShadowEnemyx/serien-sammler/releases/latest). Python wird nicht benötigt.

- **Windows:** `Serien-Sammler-Windows-x64.zip` herunterladen, entpacken und `Serien-Sammler.exe` starten.
- **Mac mit Apple Silicon:** `Serien-Sammler-macOS-Apple-Silicon.zip` herunterladen, entpacken und `Serien-Sammler.app` öffnen.
- **Intel-Mac:** `Serien-Sammler-macOS-Intel.zip` herunterladen, entpacken und `Serien-Sammler.app` öffnen.

Die erste Version ist nicht offiziell signiert. Unter Windows kann SmartScreen **Weitere Informationen → Trotzdem ausführen** verlangen. Unter macOS die App per Rechtsklick → **Öffnen** starten und nochmals **Öffnen** bestätigen. Downloads sollten nur aus diesem Repository stammen; zur zusätzlichen Kontrolle liegt `SHA256SUMS.txt` bei.

## Funktionen

- Deutsche und englische Oberfläche mit automatischer Spracherkennung
- Rekursive Suche durch alle Unterordner
- Flexible Suche: `Ghost Whisperer` findet auch `Ghost.Whisperer`, `Ghost-Whisperer` und `GhostWhisperer`
- Vorschau mit Videos, Untertiteln, neuen und vorhandenen Dateien
- Fortschrittsanzeige und sicheres Abbrechen zwischen Dateien
- Merkt sich Suchordner, Zielordner und Sprache
- Ergänzt bei späteren Durchläufen nur neue Dateien
- Überschreibt niemals vorhandene Dateien
- Unterstützt `.mkv`, `.mp4`, `.srt`, `.ass`, `.ssa`, `.vtt` und `.sub`

Originaldateien werden ausschließlich **kopiert**, nie verschoben oder gelöscht. Der Zielordner darf nicht innerhalb des Suchordners liegen.

## Start aus dem Quellcode

Beim Start aus dem Quellcode wird Python 3.9 oder neuer benötigt.

```bash
python3 serien_sammler.py \
  --source "/Pfad/zum/Download-Ordner" \
  --destination "/Pfad/zum/Video-Ordner" \
  --series "Ghost Whisperer" \
  --language de \
  --preview
```

Ohne `--preview` werden die Dateien kopiert. Mit `--remember-folders` werden die ausgewählten Ordner gespeichert. Die vorhandenen `.command`- und `.bat`-Startdateien bleiben als Quellcode-Fallback erhalten.

## Entwicklung

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

PyInstaller ist in `requirements-build.txt` fest angeheftet. Versions-Tags wie `v1.0.0` führen automatisch alle Tests aus und veröffentlichen Downloads für Windows x64, macOS Apple Silicon und macOS Intel.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
