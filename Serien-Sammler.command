#!/bin/zsh
# Per Doppelklick auf macOS starten. Die Eingabe erfolgt über macOS-Dialoge.
cd "$(dirname "$0")"

PYTHON_EXECUTABLE="/usr/bin/python3"
SOURCE_FOLDER="$($PYTHON_EXECUTABLE serien_sammler.py --config-value source)"
DESTINATION_FOLDER="$($PYTHON_EXECUTABLE serien_sammler.py --config-value destination)"

if [[ -d "$SOURCE_FOLDER" && -d "$DESTINATION_FOLDER" ]]; then
  export SAVED_SOURCE="$SOURCE_FOLDER"
  export SAVED_DESTINATION="$DESTINATION_FOLDER"
  FOLDER_CHOICE=$(
    /usr/bin/osascript <<'APPLESCRIPT'
set dialogText to "Gespeicherte Ordner verwenden?" & return & return & "Suchordner: " & (system attribute "SAVED_SOURCE") & return & "Zielordner: " & (system attribute "SAVED_DESTINATION")
try
  button returned of (display dialog dialogText buttons {"Abbrechen", "Ändern", "Verwenden"} default button "Verwenden" cancel button "Abbrechen" with title "Serien-Sammler")
on error number -128
  return "Abbrechen"
end try
APPLESCRIPT
  )
  [[ "$FOLDER_CHOICE" == "Abbrechen" ]] && exit 0
  if [[ "$FOLDER_CHOICE" == "Ändern" ]]; then
    SOURCE_FOLDER=""
    DESTINATION_FOLDER=""
  fi
fi

if [[ -z "$SOURCE_FOLDER" || -z "$DESTINATION_FOLDER" ]]; then
  SOURCE_FOLDER=$(
    /usr/bin/osascript <<'APPLESCRIPT'
try
  POSIX path of (choose folder with prompt "Ordner auswählen, in dem gesucht werden soll:")
on error number -128
  return ""
end try
APPLESCRIPT
  )
  [[ -z "$SOURCE_FOLDER" ]] && exit 0

  DESTINATION_FOLDER=$(
    /usr/bin/osascript <<'APPLESCRIPT'
try
  POSIX path of (choose folder with prompt "Zielordner auswählen (darin entsteht der Serienordner):")
on error number -128
  return ""
end try
APPLESCRIPT
  )
  [[ -z "$DESTINATION_FOLDER" ]] && exit 0
fi

SERIES_NAME=$(
  /usr/bin/osascript <<'APPLESCRIPT'
try
  text returned of (display dialog "Name der Serie eingeben:" default answer "" buttons {"Abbrechen", "Suchen"} default button "Suchen" cancel button "Abbrechen" with title "Serien-Sammler")
on error number -128
  return ""
end try
APPLESCRIPT
)
[[ -z "$SERIES_NAME" ]] && exit 0

PREVIEW_OUTPUT="$($PYTHON_EXECUTABLE serien_sammler.py --source "$SOURCE_FOLDER" --destination "$DESTINATION_FOLDER" --series "$SERIES_NAME" --preview 2>&1)"
PREVIEW_STATUS=$?
export PREVIEW_OUTPUT

if [[ $PREVIEW_STATUS -ne 0 ]]; then
  /usr/bin/osascript <<'APPLESCRIPT'
display alert "Serien-Sammler" message (system attribute "PREVIEW_OUTPUT") as warning
APPLESCRIPT
  exit $PREVIEW_STATUS
fi

CONFIRM_COPY=$(
  /usr/bin/osascript <<'APPLESCRIPT'
try
  button returned of (display dialog (system attribute "PREVIEW_OUTPUT") & return & return & "Jetzt kopieren?" buttons {"Abbrechen", "Kopieren"} default button "Kopieren" cancel button "Abbrechen" with title "Vorschau")
on error number -128
  return "Abbrechen"
end try
APPLESCRIPT
)

if [[ "$CONFIRM_COPY" == "Kopieren" ]]; then
  $PYTHON_EXECUTABLE serien_sammler.py --source "$SOURCE_FOLDER" --destination "$DESTINATION_FOLDER" --series "$SERIES_NAME" --remember-folders
fi
