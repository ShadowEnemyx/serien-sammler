# Serien-Sammler

[English README](README.md)

Eine kleine macOS-App, die Folgen einer Serie aus vielen Unterordnern in einem einzigen Ordner sammelt.

Die Originaldateien werden ausschließlich **kopiert**, nie verschoben oder gelöscht.

## Verwendung auf macOS

1. `Serien-Sammler.command` per Doppelklick öffnen. Beim ersten Start kann macOS eine Bestätigung über Rechtsklick → **Öffnen** verlangen.
2. Den Ordner wählen, in dem nach Folgen gesucht werden soll. Alle Unterordner werden durchsucht.
3. Den Zielordner wählen, zum Beispiel einen Ordner namens `Filme`.
4. Den Namen der gewünschten Serie eingeben, zum Beispiel `Ghost Whisperer`.
5. Das Programm erstellt im Zielordner automatisch `Ghost Whisperer`, sammelt dort alle passenden `.mkv`- und `.mp4`-Dateien und öffnet den Ordner anschließend im Finder.

Die Suche ignoriert Punkte, Kommas, Leerzeichen und Bindestriche. `Ghost Whisperer` findet deshalb auch `Ghost.Whisperer...`, `Ghost-Whisperer...` und `GhostWhisperer...`. macOS-Metadateien mit `._` werden nicht kopiert. Das Programm merkt sich kopierte Quelldateien in einer versteckten Datei im Serienordner; bei einem späteren Durchlauf werden daher nur neue Folgen ergänzt. Bei verschiedenen Quelldateien mit gleichem Namen wird nichts überschrieben; stattdessen wird ` (2)`, ` (3)` usw. angehängt.

## Verwendung unter Windows

1. Python 3 von [python.org](https://www.python.org/downloads/windows/) installieren. Bei der Installation **Add Python to PATH** aktivieren.
2. `Serien-Sammler.bat` per Doppelklick starten.
3. Suchordner und Zielordner auswählen sowie den Seriennamen eingeben.

Der fertige Serienordner öffnet sich automatisch im Windows-Explorer.

## Start im Terminal

```bash
/usr/bin/python3 serien_sammler.py \
  --source "/Pfad/zum/Download-Ordner" \
  --destination "/Pfad/zum/Filme-Ordner" \
  --series "Ghost Whisperer"
```

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE). Es darf genutzt, verändert und weitergegeben werden, solange der Lizenzhinweis erhalten bleibt.
