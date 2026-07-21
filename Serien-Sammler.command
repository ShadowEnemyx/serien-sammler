#!/bin/zsh
# Per Doppelklick auf macOS starten. Die Eingabe erfolgt über einen macOS-Dialog.
cd "$(dirname "$0")"
SOURCE_FOLDER=$(
  /usr/bin/osascript <<'APPLESCRIPT'
try
  POSIX path of (choose folder with prompt "Ordner auswählen, in dem gesucht werden soll:")
on error number -128
  return ""
end try
APPLESCRIPT
)

DESTINATION_FOLDER=$(
  /usr/bin/osascript <<'APPLESCRIPT'
try
  POSIX path of (choose folder with prompt "Zielordner auswählen (darin entsteht der Serienordner):")
on error number -128
  return ""
end try
APPLESCRIPT
)

SERIES_NAME=$(
  /usr/bin/osascript <<'APPLESCRIPT'
try
  text returned of (display dialog "Name der Serie eingeben:" default answer "" buttons {"Abbrechen", "Suchen"} default button "Suchen" cancel button "Abbrechen" with title "Serien-Sammler für HandBrake")
on error number -128
  return ""
end try
APPLESCRIPT
)

if [[ -n "$SOURCE_FOLDER" && -n "$DESTINATION_FOLDER" && -n "$SERIES_NAME" ]]; then
  /usr/bin/python3 serien_sammler.py --source "$SOURCE_FOLDER" --destination "$DESTINATION_FOLDER" --series "$SERIES_NAME"
fi
