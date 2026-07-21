# Serien-Sammler für HandBrake

Eine kleine macOS-App, die Folgen einer Serie aus vielen Unterordnern in einem einzigen Ordner sammelt. So kann der fertige Serienordner direkt in HandBrake gezogen werden.

Die Originaldateien werden ausschließlich **kopiert**, nie verschoben oder gelöscht.

## Verwendung auf macOS

1. `Serien-Sammler.command` per Doppelklick öffnen. Beim ersten Start kann macOS eine Bestätigung über Rechtsklick → **Öffnen** verlangen.
2. Den Ordner wählen, in dem nach Folgen gesucht werden soll. Alle Unterordner werden durchsucht.
3. Den Zielordner wählen, zum Beispiel einen Ordner namens `Filme`.
4. Den Namen der gewünschten Serie eingeben, zum Beispiel `Ghost Whisperer`.
5. Das Programm erstellt im Zielordner automatisch `Ghost Whisperer` und kopiert alle passenden `.mkv`- und `.mp4`-Dateien hinein. Der fertige Ordner öffnet sich anschließend im Finder.

Die Suche ignoriert Punkte, Kommas, Leerzeichen und Bindestriche. Die Eingabe `Ghost Whisperer` findet deshalb auch `Ghost.Whisperer...`, `Ghost-Whisperer...` und `GhostWhisperer...`. macOS-Metadateien mit `._` werden nicht kopiert. Bei gleichen Dateinamen wird nichts überschrieben; stattdessen wird ` (2)`, ` (3)` usw. angehängt.

## Start im Terminal

```bash
/usr/bin/python3 serien_sammler.py \
  --source "/Pfad/zum/Download-Ordner" \
  --destination "/Pfad/zum/Filme-Ordner" \
  --series "Ghost Whisperer"
```

## Auf GitHub veröffentlichen

1. Auf GitHub ein neues leeres Repository erstellen, zum Beispiel `serien-sammler`.
2. Im Projektordner diese Befehle ausführen:

   ```bash
   git init
   git add serien_sammler.py Serien-Sammler.command README.md
   git commit -m "Erste Version des Serien-Sammlers"
   git branch -M main
   git remote add origin https://github.com/DEIN-NAME/serien-sammler.git
   git push -u origin main
   ```

Danach können andere Personen das Repository als ZIP herunterladen. Die Ordner werden bei jedem Start über Finder-Auswahldialoge festgelegt, daher muss niemand den Code bearbeiten.
