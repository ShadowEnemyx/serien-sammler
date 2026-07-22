# Serien-Sammler

[English README](README.md)

Der Serien-Sammler findet passende Video- und Untertiteldateien in verschachtelten Ordnern und sammelt sie sicher in einem Zielordner. Originaldateien werden nur kopiert, niemals verschoben oder gelöscht.

## Download

Die aktuelle fertige Version gibt es unter [GitHub Releases](https://github.com/ShadowEnemyx/serien-sammler/releases/latest). Python wird nicht benötigt.

- **Windows-Installer:** `Serien-Sammler-Windows-x64-Setup.exe`
- **Windows portabel:** `Serien-Sammler-Windows-x64.zip`
- **Mac mit Apple Silicon:** `Serien-Sammler-macOS-Apple-Silicon.dmg` oder das gleichnamige ZIP
- **Intel-Mac:** `Serien-Sammler-macOS-Intel.dmg` oder das gleichnamige ZIP

Builds werden automatisch signiert, sobald der Repository-Besitzer Signierungszertifikate hinterlegt hat. `BUILD-STATUS.txt` im Paket zeigt, ob der konkrete Build signiert ist. Bei einem unsignierten Windows-Build kann SmartScreen **Weitere Informationen → Trotzdem ausführen** verlangen. Unter macOS die unsignierte App per Rechtsklick → **Öffnen** starten und nochmals bestätigen. Nur aus diesem Repository herunterladen; `SHA256SUMS.txt` ermöglicht eine zusätzliche Prüfung.

## Funktionen

- Deutsche und englische Oberfläche mit automatischer Spracherkennung
- Rekursive Suche in allen Unterordnern
- Flexible Suche: `Ghost Whisperer` findet auch `Ghost.Whisperer`, `Ghost-Whisperer` und `GhostWhisperer`
- Einstufung als sicherer, wahrscheinlicher oder mehrdeutiger Treffer; mehrdeutige Dateien müssen bewusst ausgewählt werden
- Automatische Staffelordner: `S01E03`, `Staffel 2`, `Season 3` und `4x05` werden nach `S01`, `S02`, `S03` und `S04` sortiert
- Bereits gesammelte Folgen im Serien-Hauptordner werden beim nächsten Lauf sicher in die erkannte Staffel einsortiert
- Auswählbare Vorschau mit Quellpfad und geplanter Aktion: kopieren, überspringen oder umbenennen
- Inhaltsfingerabdrücke verhindern Dubletten auch bei anderem Quellpfad oder Dateinamen
- Verschiedene Dateien mit gleichem Namen bleiben als ` (2)`, ` (3)` usw. erhalten
- Geprüfte temporäre Kopien, Fortschrittsanzeige und sicheres Abbrechen zwischen Dateien
- Optionale tägliche Update-Benachrichtigung und manuelle Update-Prüfung
- Lokale rotierende Protokolle und exportierbarer Diagnosebericht; keine Telemetrie
- Unterstützt `.mkv`, `.mp4`, `.srt`, `.ass`, `.ssa`, `.vtt` und `.sub`

Der Zielordner darf nicht innerhalb des Suchordners liegen. Vorhandene Manifeste der Version 1 und alte Konfigurationsdateien werden automatisch übernommen.

## Kommandozeile

Beim Start aus dem Quellcode wird Python 3.9 oder neuer benötigt.

```bash
python3 serien_sammler.py \
  --source "/Pfad/zum/Download-Ordner" \
  --destination "/Pfad/zum/Zielordner" \
  --series "Ghost Whisperer" \
  --language de \
  --preview
```

Ohne `--preview` werden Dateien kopiert. Weitere Optionen sind `--remember-folders`, `--include-ambiguous`, `--check-updates` und `--log-file /Pfad/zum/Protokoll.txt`. Die `.command`-, `.bat`- und PowerShell-Dateien bleiben als Quellcode-Fallback erhalten.

## Entwicklung und Releases

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

PyInstaller und Pillow sind in `requirements-build.txt` fest angeheftet. Tags wie `v1.2.0` testen und bauen Windows x64, macOS Apple Silicon und macOS Intel, prüfen Installer und DMGs, erzeugen SHA-256-Prüfsummen und veröffentlichen das Release.

Optionale GitHub-Actions-Secrets aktivieren die offizielle Signierung:

- Windows: `WINDOWS_CERTIFICATE_BASE64`, `WINDOWS_CERTIFICATE_PASSWORD`
- Apple: `APPLE_CERTIFICATE_BASE64`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD`

Ohne diese Secrets veröffentlicht derselbe Workflow bewusst eindeutig markierte, unsignierte Builds. Apple-Zertifikate benötigen eine Apple-Developer-Mitgliedschaft; ein vertrauenswürdiges Windows-Code-Signing-Zertifikat muss separat beschafft werden.

## Datenschutz und Lizenz

Die Update-Prüfung greift ausschließlich auf die öffentliche GitHub-Releases-API zu und kann deaktiviert werden. Protokolle bleiben lokal. Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
