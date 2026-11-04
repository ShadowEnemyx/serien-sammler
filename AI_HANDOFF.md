# KI-Übergabe: Serien-Sammler

Stand: 12. August 2026 · aktuelle veröffentlichte Version: **1.6.8**

Diese Datei ist der Arbeitskontext für eine andere KI oder Entwicklerin/einen anderen Entwickler. Sie erklärt, was das Projekt macht, welche Entscheidungen bereits getroffen wurden und worauf bei Änderungen unbedingt zu achten ist.

## Projektziel

**Serien-Sammler** ist eine Desktop-App für macOS und Windows. Sie findet Video- und Untertiteldateien einer Serie in einem frei wählbaren Suchordner, einschließlich aller Unterordner, und sammelt sie in einem Serien-Zielordner.

Beispiel:

```text
Suchordner/
  unterschiedliche Download- und Release-Ordner/
    Ghost.Whisperer.S01E01....mkv
    GhostWhispererS01E02....mkv

Zielordner/
  Ghost Whisperer/
    S01/
      Ghost.Whisperer.S01E01....mkv
      GhostWhispererS01E02....mkv
```

Die App ist allgemein gehalten; HandBrake war nur der ursprüngliche persönliche Anwendungsfall und darf weder im App-Namen noch in der öffentlichen Beschreibung im Vordergrund stehen.

Repository: <https://github.com/ShadowEnemyx/serien-sammler>

Aktueller Release: <https://github.com/ShadowEnemyx/serien-sammler/releases/latest>

## Bedienung und Fachlogik

- Nutzer wählen Suchordner, Zielordner und Serienname in der Tkinter-Oberfläche.
- Der Serienname wird flexibel normalisiert: Leerzeichen, Punkte, Bindestriche und zusammengeschriebene Schreibweisen werden gleich behandelt. `Ghost Whisperer` findet daher auch `Ghost.Whisperer`, `Ghost-Whisperer` und `GhostWhisperer`.
- Der Name darf nur in einem übergeordneten Ordner stehen; Dateien wie `S01E01.mkv` werden trotzdem gefunden.
- Unterstützte Dateien:
  - Video: `.avi`, `.mkv`, `.mp4`
  - Untertitel: `.srt`, `.ass`, `.ssa`, `.vtt`
  - `.sub` wird absichtlich ignoriert.
- Dateien mit `sample` irgendwo im Dateinamen werden unabhängig von Groß-/Kleinschreibung immer ignoriert.
- Papierkörbe werden nicht durchsucht: macOS `.Trashes`, Linux-Varianten und Windows `$RECYCLE.BIN` sind ausgeschlossen.
- Staffeln werden aus Mustern wie `S01E03`, `Staffel 2`, `Season 3` und `4x05` erkannt und in `S01`, `S02`, usw. einsortiert.
- Gleichnamige, aber unterschiedliche Dateien werden als ` (2)`, ` (3)` usw. erhalten. Identische Inhalte werden anhand eines Fingerprints nicht doppelt kopiert.

### Trefferqualität und Auswahl

Jeder Treffer wird als `Sicher`, `Wahrscheinlich` oder `Mehrdeutig` eingestuft:

- Sichere und wahrscheinliche neue Treffer sind in einer frischen Vorschau vorausgewählt.
- Mehrdeutige Treffer bleiben zunächst absichtlich **nicht** ausgewählt, um Fehlkopien bei einer sehr kurzen Suche (zum Beispiel nur `Marvel`) zu vermeiden.
- Der Nutzer kann einzelne Zeilen per Doppelklick oder Leertaste umschalten.
- Seit **1.6.7** gibt es die Checkbox **„Alle Treffer auswählen (auch mehrdeutige)”**. Sie erlaubt nach bewusster Kontrolle, alle verarbeitbaren Treffer mit einem Klick zu markieren.
- Seit **1.6.8** steht diese Checkbox links direkt über der Tabelle. Sie darf keine zusätzliche rechte Grid-Spalte erzeugen oder die Tabellenbreite einschränken.
- Ein Umschalten zwischen Kopieren und Ausschneiden nach der Vorschau darf die Vorschau nicht löschen. Das ist seit 1.6.6 implementiert.

## Kopieren und Ausschneiden: Sicherheitsregeln

Die folgenden Regeln sind wichtig und dürfen nicht leichtfertig abgeschwächt werden:

1. **Kopieren** behält immer die Originaldateien.
2. **Ausschneiden** kopiert zuerst in eine temporäre Datei, prüft Inhalt und Fingerprint und verschiebt das Original erst danach in den Papierkorb.
3. Es gibt kein direktes, endgültiges Löschen von Medien durch die App.
4. Wenn nach erfolgreicher Verarbeitung keine relevanten Serien-Mediendateien mehr in einem Quell-Release-Ordner liegen, wird der ganze passende Quellordner in den System-Papierkorb verschoben. Übrige `.txt`- oder andere Begleitdateien dürfen dabei mit in den Papierkorb.
5. Sind noch relevante, nicht ausgewählte oder fehlgeschlagene Medien dort, wird nur die erfolgreich verarbeitete Einzeldatei in den Papierkorb verschoben.
6. Der konfigurierte Such-Hauptordner selbst darf niemals verschoben oder gelöscht werden.
7. Abbrechen ist zwischen Dateien möglich; bereits erfolgreiche Kopien bleiben korrekt erhalten und im Manifest gespeichert.

Die plattformabhängige Papierkorb-Logik liegt in `series_collector/trash.py`. Unter macOS wird Finder/AppleScript mit einem Alias verwendet, damit auch Pfade mit Sonderzeichen korrekt verarbeitet werden.

## Architektur und wichtige Dateien

```text
series_collector/
  core.py           Such-, Auswahl-, Manifest-, Fingerprint- und Kopierlogik
  gui.py            Tkinter-Desktop-Oberfläche
  cli.py            Kommandozeilenoberfläche
  trash.py          Papierkorb-Integration für macOS, Windows und Linux
  updates.py        GitHub-Release-Prüfung und geprüfte Selbstaktualisierung
  i18n.py           Deutsche und englische Texte
  logging_utils.py  Lokales Logging und Diagnoseberichte
  __init__.py       Einzige zentrale Versionsnummer
tests/
  test_core.py      Kern- und Integrationsfälle
  test_cli.py       CLI-Smoke-Tests
  test_updates.py   Update- und Prüfsummenlogik
.github/workflows/
  tests.yml         Tests auf Linux, macOS und Windows bei Push/PR
  release.yml       Builds, Smoke-Tests, Checksummen und GitHub Release bei v-Tags
```

Weitere Einstiegspunkte:

- `serien_sammler.py`: kompatibler Python-/CLI-Startpunkt
- `Serien-Sammler.command`, `.bat` und PowerShell-Skript: Quellcode-Fallbacks
- `Serien-Sammler.spec`: PyInstaller-Konfiguration
- `README.de.md` und `README.md`: öffentliche Anleitung auf Deutsch/Englisch

## Speicherung auf dem Benutzergerät

- Konfiguration: `~/.serien-sammler-config.json`
  - enthält Suchordner, Zielordner, Sprache, Update-Einstellung und Zeitpunkt der letzten Update-Prüfung
- Manifest pro Serien-Zielordner: `.serien-sammler-manifest.json`
  - speichert Fingerprints und schon verarbeitete Dateien
- Protokolle: je nach Betriebssystem im Benutzer-Logordner; Diagnosebericht kann aus der App exportiert werden
- Es gibt keine Telemetrie. Die Update-Prüfung ruft nur die öffentliche GitHub-Releases-API auf.

Keine persönlichen Pfade in den Quellcode, die README oder Releases eintragen. Die App soll mit frei wählbaren Ordnern auf jedem Mac oder Windows-PC funktionieren.

## Updates und Releases

- Die App prüft optional täglich sowie auf Wunsch manuell auf die neueste GitHub-Version.
- `series_collector/updates.py` verwendet das Repository `ShadowEnemyx/serien-sammler`, lädt das passende ZIP herunter und prüft es gegen `SHA256SUMS.txt`.
- Das frühere macOS-Problem `CERTIFICATE_VERIFY_FAILED` wurde durch die Verwendung von Certifi behoben. Diese Prüfung nicht durch unsichere SSL-Deaktivierung ersetzen.
- Builds sind ohne hinterlegte Zertifikats-Secrets bewusst als unsigniert markiert. Die README erklärt Gatekeeper/SmartScreen.

### Release-Ablauf

1. Version in `series_collector/__init__.py` erhöhen.
2. Bei Funktionsänderungen Tests ergänzen oder anpassen.
3. Tests lokal ausführen:

   ```bash
   python -m pip install -r requirements-dev.txt
   python -m pytest
   ```

4. Für einen Release einen Tag passend zur Versionsnummer pushen, zum Beispiel `v1.6.9`.
5. Der GitHub-Workflow baut automatisch:
   - Windows x64: Setup und portables ZIP
   - macOS Apple Silicon: DMG und ZIP
   - macOS Intel: DMG und ZIP
6. Der Workflow testet die erstellten Programme mit `--version`, erstellt `SHA256SUMS.txt` und veröffentlicht das GitHub Release.
7. Vor dem Abschluss prüfen, dass der Release-Workflow erfolgreich war und die Assets vorhanden sind.

Bei GitHub-Veröffentlichungen absichtlich arbeiten: nur die zugehörigen Dateien committen, Pull Request prüfen/mergen, Tag erstellen, Release-Build abwarten.

## Bisherige wichtige Änderungen

| Version | Inhalt |
| --- | --- |
| 1.6.0–1.6.3 | Ausschneiden sicher über den Papierkorb; Finder-Pfadfix; erst alle verschachtelten Medien fertig verarbeiten, bevor ein Release-Ordner im Papierkorb landet |
| 1.6.4 | `.sub` ignorieren |
| 1.6.5 | System-Papierkörbe nicht mehr durchsuchen |
| 1.6.6 | Vorschau beim Wechsel zwischen Kopieren/Ausschneiden behalten |
| 1.6.7 | Checkbox zum bewussten Auswählen aller Treffer, auch mehrdeutiger |
| 1.6.8 | Checkbox-Layout korrigiert: links über der Tabelle, volle Tabellenbreite |

## GitHub-Aufräumen

Am 12. August 2026 wurden 51 alte GitHub-Actions-Artefakte (rund 1,25 GB) gelöscht. Sie waren nur doppelte Zwischen-Builds; die eigentlichen Downloads in den Releases wurden **nicht** gelöscht. Die drei aktuellen Zwischen-Artefakte von v1.6.8 bleiben bestehen.

Aktuell offene Pull Requests sind Dependabot-Vorschläge für PyInstaller, Pytest und Pillow. Sie sind nicht Müll und sollten bei Gelegenheit geprüft, getestet und dann getrennt gemergt oder geschlossen werden.

Alte Releases bleiben bewusst erhalten, damit Nutzer bei Problemen eine frühere Version herunterladen können. Nicht ohne ausdrücklichen Wunsch löschen.

## Sinnvolle nächste Schritte (nicht automatisch umgesetzt)

- Dependabot-Updates einzeln prüfen, besonders PyInstaller, weil es die Build-Pipeline beeinflusst.
- Bei größeren UI-Änderungen die Oberfläche auf Mac und Windows visuell kontrollieren; Tkinter-Grid-Spalten/-Zeilen können sonst ungewollte Leerflächen oder schmale Tabellen erzeugen.
- Code-Signing-Zertifikate einrichten, wenn die Verteilung ohne macOS-Gatekeeper- bzw. Windows-SmartScreen-Hinweise erfolgen soll.
- Vor weiteren Funktionen zuerst prüfen, ob sie die sicheren Auswahl- und Papierkorb-Regeln gefährden.

## Kommunikationsstil mit dem Nutzer

Der Nutzer schreibt auf Deutsch und möchte einfache, direkte Erklärungen. Praktische Schritte und konkrete Ergebnisse sind wichtiger als technische Theorie. Bei riskanten Dateivorgängen klar sagen, dass Originale im Papierkorb landen und wiederherstellbar sind. Keine persönlichen Ordnerpfade als feste Voreinstellung einbauen.
