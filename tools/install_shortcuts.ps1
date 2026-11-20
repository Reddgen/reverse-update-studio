param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = "Stop"
$ws = New-Object -ComObject WScript.Shell
$cmd = $env:ComSpec
$launch = Join-Path $Target "Launch.cmd"
$uninstall = Join-Path $Target "Uninstall.cmd"
$icon = Join-Path $Target "setup.ico"
if (-not (Test-Path $icon)) { $icon = "$env:SystemRoot\System32\shell32.dll,137" }

function New-Link($path, $arguments, $workdir, $description) {
  $dir = Split-Path -Parent $path
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $sc = $ws.CreateShortcut($path)
  $sc.TargetPath = $cmd
  $sc.Arguments = $arguments
  $sc.WorkingDirectory = $workdir
  $sc.WindowStyle = 7
  $sc.Description = $description
  $sc.IconLocation = $icon
  $sc.Save()
  if (-not (Test-Path $path)) { throw "shortcut was not created: $path" }
}

try {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $startDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Reverse Update Studio"

  New-Link (Join-Path $desktop "Reverse Update Studio.lnk") "/c `"`"$launch`"`"" $Target "Reverse Update Studio"
  New-Link (Join-Path $desktop "Uninstall Reverse Update Studio.lnk") "/c `"`"$uninstall`"`"" $Target "Uninstall Reverse Update Studio"
  New-Link (Join-Path $startDir "Reverse Update Studio.lnk") "/c `"`"$launch`"`"" $Target "Reverse Update Studio"
  New-Link (Join-Path $startDir "Uninstall Reverse Update Studio.lnk") "/c `"`"$uninstall`"`"" $Target "Uninstall Reverse Update Studio"

  Write-Host "Shortcuts verified: Desktop and Start Menu."
  exit 0
} catch {
  Write-Host "SHORTCUT ERROR: $($_.Exception.Message)"
  exit 1
}
