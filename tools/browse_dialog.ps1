param(
    [ValidateSet("file", "folder")][string]$Kind = "file",
    [string]$Title = "Select"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($Kind -eq "folder") {
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Title
    $dialog.ShowNewFolderButton = $true
} else {
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = $Title
    $dialog.CheckFileExists = $true
    $dialog.Multiselect = $false
    $dialog.Filter = "All files (*.*)|*.*|Executables and ELF (*.exe;*.dll;*.elf)|*.exe;*.dll;*.elf|CSV (*.csv)|*.csv"
}

$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    if ($Kind -eq "folder") { @{ path = $dialog.SelectedPath } | ConvertTo-Json -Compress }
    else { @{ path = $dialog.FileName } | ConvertTo-Json -Compress }
} else {
    @{ cancelled = $true } | ConvertTo-Json -Compress
}
