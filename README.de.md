# Serien-Sammler

[English README](README.md)

Eine kleine App für macOS und Windows, die Folgen einer Serie und die passenden Untertitel aus vielen Unterordnern in einem einzigen Ordner sammelt.

Die Originaldateien werden ausschließlich **kopiert**, nie verschoben oder gelöscht.

## Verwendung auf macOS

1. `Serien-Sammler.command` per Doppelklick öffnen. Beim ersten Start kann macOS eine Bestätigung über Rechtsklick → **Öffnen** verlangen.
2. Beim ersten Start den Suchordner und den Zielordner wählen. Diese Ordner werden gespeichert; bei späteren Starts können sie wiederverwendet oder geändert werden.
3. Den Namen der gewünschten Serie eingeben, zum Beispiel `Ghost Whisperer`.
4. In der Vorschau prüfen, wie viele Dateien gefunden, neu oder bereits vorhanden sind, und das Kopieren bestätigen.
5. Das Programm erstellt im Zielordner automatisch `Ghost Whisperer`, kopiert nur die neuen passenden Dateien und öffnet den Ordner anschließend im Finder.

Unterstützte Videoformate sind `.mkv` und `.mp4`. Passende Untertitel in den Formaten `.srt`, `.ass`, `.ssa`, `.vtt` und `.sub` werden ebenfalls gesammelt.

Die Suche ignoriert Punkte, Kommas, Leerzeichen und Bindestriche. `Ghost Whisperer` findet deshalb auch `Ghost.Whisperer...`, `Ghost-Whisperer...` und `GhostWhisperer...`. macOS-Metadateien mit `._` werden nicht kopiert. Das Programm merkt sich kopierte Quelldateien in einer versteckten Datei im Serienordner; bei einem späteren Durchlauf werden daher nur neue Folgen und Untertitel ergänzt. Bei verschiedenen Quelldateien mit gleichem Namen wird nichts überschrieben; stattdessen wird ` (2)`, ` (3)` usw. angehängt.

## Verwendung unter Windows

1. Python 3 von [python.org](https://www.python.org/downloads/windows/) installieren. Bei der Installation **Add Python to PATH** aktivieren.
2. `Serien-Sammler.bat` per Doppelklick starten.
3. Beim ersten Start Suchordner und Zielordner auswählen. Bei späteren Starts können die gespeicherten Ordner wiederverwendet oder geändert werden.
4. Seriennamen eingeben, die Vorschau prüfen und das Kopieren bestätigen.

Der fertige Serienordner öffnet sich automatisch im Windows-Explorer.

## Start im Terminal

```bash
/usr/bin/python3 serien_sammler.py \
  --source "/Pfad/zum/Download-Ordner" \
  --destination "/Pfad/zum/Filme-Ordner" \
  --series "Ghost Whisperer" \
  --remember-folders
```

Mit `--preview` werden die geplanten Änderungen angezeigt, ohne Dateien zu kopieren. Nachdem die Ordner gespeichert wurden, können `--source` und `--destination` weggelassen werden.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE). Es darf genutzt, verändert und weitergegeben werden, solange der Lizenzhinweis erhalten bleibt.
