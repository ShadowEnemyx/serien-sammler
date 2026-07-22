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

if (Get-Command py -ErrorAction SilentlyContinue) {
    $usePythonLauncher = $true
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $usePythonLauncher = $false
} else {
    [System.Windows.Forms.MessageBox]::Show(
        "Python 3 wurde nicht gefunden. Bitte zuerst von python.org installieren und danach erneut starten.",
        "Serien-Sammler"
    )
    exit
}

function Invoke-SeriesCollector([string[]]$CollectorArguments) {
    if ($script:usePythonLauncher) {
        & py -3 "$PSScriptRoot\serien_sammler.py" @CollectorArguments
    } else {
        & python "$PSScriptRoot\serien_sammler.py" @CollectorArguments
    }
}

$source = (Invoke-SeriesCollector -CollectorArguments @("--config-value", "source") | Out-String).Trim()
$destination = (Invoke-SeriesCollector -CollectorArguments @("--config-value", "destination") | Out-String).Trim()

if ($source -and $destination -and
    (Test-Path -LiteralPath $source -PathType Container) -and
    (Test-Path -LiteralPath $destination -PathType Container)) {
    $folderChoice = [System.Windows.Forms.MessageBox]::Show(
        "Gespeicherte Ordner verwenden?`n`nSuchordner: $source`nZielordner: $destination",
        "Serien-Sammler",
        [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    if ($folderChoice -eq [System.Windows.Forms.DialogResult]::Cancel) { exit }
    if ($folderChoice -eq [System.Windows.Forms.DialogResult]::No) {
        $source = $null
        $destination = $null
    }
}

if (-not $source -or -not $destination) {
    $source = Select-Folder "Ordner auswählen, in dem nach Serienfolgen gesucht werden soll"
    if (-not $source) { exit }

    $destination = Select-Folder "Zielordner auswählen, in dem der Serienordner erstellt wird"
    if (-not $destination) { exit }
}

$seriesName = [Microsoft.VisualBasic.Interaction]::InputBox(
    "Name der Serie eingeben:",
    "Serien-Sammler"
)
if ([string]::IsNullOrWhiteSpace($seriesName)) { exit }

$previewLines = @(Invoke-SeriesCollector -CollectorArguments @(
    "--source", $source,
    "--destination", $destination,
    "--series", $seriesName,
    "--preview"
) 2>&1)
$previewStatus = $LASTEXITCODE
$previewText = ($previewLines | Out-String).Trim()

if ($previewStatus -ne 0) {
    [System.Windows.Forms.MessageBox]::Show(
        $previewText,
        "Serien-Sammler",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    exit
}

$copyChoice = [System.Windows.Forms.MessageBox]::Show(
    "$previewText`n`nJetzt kopieren?",
    "Vorschau",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)

if ($copyChoice -eq [System.Windows.Forms.DialogResult]::Yes) {
    Invoke-SeriesCollector -CollectorArguments @(
        "--source", $source,
        "--destination", $destination,
        "--series", $seriesName,
        "--remember-folders"
    )
}
