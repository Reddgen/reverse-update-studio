param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = "Stop"
$Target = $Target.TrimEnd('\')
$Canon = Join-Path $env:LOCALAPPDATA "ReverseUpdateStudio"

if (-not (Test-Path (Join-Path $Target "studio\server.py"))) {
  Write-Host "This does not look like a Reverse Update Studio install:"
  Write-Host "  $Target"
  exit 1
}

Write-Host ""
Write-Host "Uninstall Reverse Update Studio"
Write-Host "-------------------------------"
Write-Host "Folder: $Target"
Write-Host ""
Write-Host "[Y] Remove app, shortcuts and data"
Write-Host "[K] Remove app and shortcuts, keep data"
Write-Host "[N] Cancel"
$answer = Read-Host "Choose"
if ($answer -match '^[Nn]') { exit 0 }
$keep = $answer -match '^[Kk]'

Write-Host "Stopping the local server..."
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like ($Target + '\*') } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (-not $env:RU_NO_SHORTCUTS -and ($Target -ieq $Canon)) {
  Write-Host "Removing shortcuts..."
  $desktop = [Environment]::GetFolderPath("Desktop")
  $startDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Reverse Update Studio"
  Remove-Item (Join-Path $desktop "Reverse Update Studio.lnk") -Force -ErrorAction SilentlyContinue
  Remove-Item (Join-Path $desktop "Uninstall Reverse Update Studio.lnk") -Force -ErrorAction SilentlyContinue
  Remove-Item $startDir -Recurse -Force -ErrorAction SilentlyContinue
} else {
  Write-Host "Skipping global shortcuts for a non-standard install folder."
}

if ($keep) {
  Write-Host "Keeping data..."
  $keepDir = Join-Path $env:LOCALAPPDATA "ReverseUpdateStudio-data"
  if (Test-Path $keepDir) { Remove-Item $keepDir -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path (Join-Path $Target "data")) { Move-Item (Join-Path $Target "data") $keepDir -Force }
  Write-Host "Data kept at: $keepDir"
}

Write-Host "Ready to remove files."
exit 0
