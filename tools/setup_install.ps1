param(
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference = "Stop"
$Source = (Resolve-Path $Source).Path.TrimEnd('\')
$Target = [IO.Path]::GetFullPath($Target).TrimEnd('\')
$Canon = Join-Path $env:LOCALAPPDATA "ReverseUpdateStudio"
$Stage = "$Target.new"
$Old = "$Target.old"
$stageActive = $false
trap {
  if ($stageActive -and (Test-Path $Stage)) { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue }
  throw
}

function Stop-TargetProcesses {
  Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Target + '\', [StringComparison]::OrdinalIgnoreCase)
  } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Free-Bytes {
  $root = [IO.Path]::GetPathRoot($Target)
  $drive = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -ieq $root } | Select-Object -First 1
  if (-not $drive) { return [long]::MaxValue }
  return [long]$drive.Free
}

function Remove-Dir($p) {
  $long = "\\?\$p"
  if (Test-Path -LiteralPath $long) { Remove-Item -LiteralPath $long -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path $p) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
}

if (-not (Test-Path (Join-Path $Source "runtime\python\python.exe"))) {
  throw "Source is missing runtime\python\python.exe"
}

$size = (Get-ChildItem $Source -Recurse -File | Measure-Object Length -Sum).Sum
$need = [long]($size * 1.15)
if ((Free-Bytes) -lt $need) {
  throw ("Not enough free space. Need {0:N0} MB, have {1:N0} MB." -f ($need/1MB), ((Free-Bytes)/1MB))
}

Write-Host "Stopping a running copy..."
Stop-TargetProcesses
Start-Sleep -Milliseconds 500

Remove-Dir $Stage
$stageActive = $true
if (Test-Path $Target) { Remove-Dir $Old }

Write-Host "Staging files..."
$robo = Start-Process robocopy.exe -ArgumentList @(
  "`"$Source`"", "`"$Stage`"", "/E", "/XD", "`"$Source\data`"", "/R:1", "/W:1",
  "/NFL", "/NDL", "/NJH", "/NJS", "/NP"
) -Wait -PassThru -NoNewWindow
if ($robo.ExitCode -ge 8) { throw "robocopy failed with $($robo.ExitCode)" }

if (-not $env:RU_SKIP_VERIFY -and (Test-Path (Join-Path $Stage "bundle-manifest.json"))) {
  Write-Host "Verifying staged bundle..."
  & (Join-Path $Stage "runtime\python\python.exe") (Join-Path $Stage "tools\verify_install.py") --base $Stage
  if ($LASTEXITCODE -ne 0) { throw "staged file verification failed" }
}

$swapped = $false
try {
  if (Test-Path $Target) {
    Rename-Item -LiteralPath $Target -NewName (Split-Path $Old -Leaf)
  }
  Rename-Item -LiteralPath $Stage -NewName (Split-Path $Target -Leaf)
  $stageActive = $false
  $swapped = $true
} catch {
  if (-not (Test-Path $Target) -and (Test-Path $Old)) {
    Rename-Item -LiteralPath $Old -NewName (Split-Path $Target -Leaf)
  }
  throw
}

# Preserve user data from the old install.
if (Test-Path (Join-Path $Old "data")) {
  if (Test-Path (Join-Path $Target "data")) { Remove-Dir (Join-Path $Target "data") }
  Move-Item -LiteralPath (Join-Path $Old "data") -Destination (Join-Path $Target "data")
}

if (Test-Path $Old) { Remove-Dir $Old }

if (-not $env:RU_NO_SHORTCUTS -and ($Target -ieq $Canon)) {
  Write-Host "Creating shortcuts..."
  & (Join-Path $Target "tools\install_shortcuts.ps1") -Target $Target
  if ($LASTEXITCODE -ne 0) { throw "shortcut creation failed" }
} else {
  Write-Host "Skipping global shortcuts for this target."
}

$json = @{ version = "0.2.0"; installed = (Get-Date).ToString("s"); path = $Target } | ConvertTo-Json -Compress
Set-Content -LiteralPath (Join-Path $Target "install.json") -Value $json -Encoding ascii
Write-Host "Install complete: $Target"
exit 0
