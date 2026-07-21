Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

function Select-Folder([string]$Description) {
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Description
    $dialog.ShowNewFolderButton = $true
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.SelectedPath
    }
    return $null
}

$source = Select-Folder "Ordner auswählen, in dem nach Serienfolgen gesucht werden soll"
if (-not $source) { exit }

$destination = Select-Folder "Zielordner auswählen, in dem der Serienordner erstellt wird"
if (-not $destination) { exit }

$seriesName = [Microsoft.VisualBasic.Interaction]::InputBox(
    "Name der Serie eingeben:",
    "Serien-Sammler"
)
if ([string]::IsNullOrWhiteSpace($seriesName)) { exit }

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "$PSScriptRoot\serien_sammler.py" --source $source --destination $destination --series $seriesName
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$PSScriptRoot\serien_sammler.py" --source $source --destination $destination --series $seriesName
} else {
    [System.Windows.Forms.MessageBox]::Show(
        "Python 3 wurde nicht gefunden. Bitte zuerst von python.org installieren und danach erneut starten.",
        "Serien-Sammler"
    )
}
