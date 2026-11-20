param(
  [Parameter(Mandatory=$true)][string]$Zip,
  [string]$WorkDir = "$env:USERPROFILE\Desktop\RU-Test"
)
$ErrorActionPreference = "Stop"
$result = [ordered]@{
  started = (Get-Date).ToString("s")
  computer = $env:COMPUTERNAME
  user = $env:USERNAME
  windows = ""
  build = ""
  arch = $env:PROCESSOR_ARCHITECTURE
  admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  zip = $Zip
  workdir = $WorkDir
  checks = [ordered]@{}
  error = ""
}
function Check($name, $ok, $detail = "") {
  $result.checks[$name] = @{ ok = [bool]$ok; detail = "$detail" }
  Write-Host ("{0}: {1} {2}" -f $name, $(if ($ok) { "PASS" } else { "FAIL" }), $detail)
}
function Save-Result {
  try {
    New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
    $result.finished = (Get-Date).ToString("s")
    $result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $WorkDir "second_pc_result.json") -Encoding UTF8
  } catch { Write-Host "Could not write result: $($_.Exception.Message)" }
}
trap {
  $result.error = $_.Exception.Message
  Check "fatal" $false $result.error
  Save-Result
  try { Stop-Transcript | Out-Null } catch {}
  Write-Host "Fatal error: $($_.Exception.Message)"
  exit 1
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Start-Transcript -Path (Join-Path $WorkDir "test.log") -Force | Out-Null

try {
  $os = Get-CimInstance Win32_OperatingSystem
  $result.windows = $os.Caption
  $result.build = $os.BuildNumber
} catch { Write-Host "OS info failed: $($_.Exception.Message)" }

$expected = "50887c2412ea55ee8095879a16058408eb56ce2ec4627587540baeb4a21ed9e4"
try {
  $actual = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
  Check "zip_hash" ($actual -eq $expected) $actual
} catch { Check "zip_hash" $false $_.Exception.Message }

try {
  $drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($env:LOCALAPPDATA).TrimEnd(':\'))
  $freeGB = [math]::Round($drive.Free / 1GB, 2)
  Check "free_space" ($freeGB -gt 3) "$freeGB GB"
} catch { Check "free_space" $false $_.Exception.Message }

$extract = Join-Path $WorkDir "src"
$src = Join-Path $extract "ReverseUpdateStudio"
try {
  if (Test-Path $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
  Write-Host "Extracting $Zip ..."
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::ExtractToDirectory($Zip, $extract)
  Check "extracted" (Test-Path (Join-Path $src "Setup.cmd")) $src
} catch {
  Check "extracted" $false $_.Exception.Message
  $result.error = "extraction failed: $($_.Exception.Message)"
  Save-Result
  try { Stop-Transcript | Out-Null } catch {}
  Write-Host "Extraction failed. Result written."
  exit 1
}

$install = Join-Path $env:LOCALAPPDATA "ReverseUpdateStudio"
try {
  $env:RU_NONINTERACTIVE = "1"
  $setupOut = cmd.exe /c "`"$src\Setup.cmd`"" 2>&1
  Check "setup_exit" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"
} catch { Check "setup_exit" $false $_.Exception.Message }
Check "install_exists" (Test-Path (Join-Path $install "studio\server.py")) $install
Check "manifest" (Test-Path (Join-Path $install "bundle-manifest.json")) ""
Check "install_json" (Test-Path (Join-Path $install "install.json")) ""

$status = $null
try {
  if (Test-Path (Join-Path $install "Launch.cmd")) {
    Start-Process -FilePath (Join-Path $install "Launch.cmd") -WindowStyle Minimized
    for ($i = 0; $i -lt 30; $i++) {
      Start-Sleep -Seconds 1
      try { $status = Invoke-RestMethod "http://127.0.0.1:8765/api/status" -TimeoutSec 2; break } catch {}
    }
  }
  Check "server_status" ($null -ne $status) ($(if ($status) { "$($status.app) $($status.version)" } else { "no response" }))
} catch { Check "server_status" $false $_.Exception.Message }

if ($status) {
  Check "ghidra" ([bool]$status.tools.ghidra) ""
  Check "rea" ([bool]$status.tools.rea) ""
  try {
    $inspect = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/inspect" -ContentType "application/json" -Body (@{ path = "$env:WINDIR\System32\notepad.exe" } | ConvertTo-Json)
    Check "inspect_notepad" ($inspect.format -like "PE*") $inspect.format
  } catch { Check "inspect_notepad" $false $_.Exception.Message }
  try {
    $trace = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/trace" -ContentType "application/json" -Body (@{ nodes = "LoadConfig,ResolvePath,ParseXML,ApplyConfig,UnknownA" } | ConvertTo-Json)
    Check "trace" ($trace.trace_id -like "tr_*") "$($trace.trace_id) priority=$($trace.priority)"
  } catch { Check "trace" $false $_.Exception.Message }
  try {
    $demo = Get-ChildItem "$install\updates_demo\dist\*.rupkg" | Sort-Object Name | Select-Object -First 1
    $verify = & "$install\runtime\python\python.exe" "$install\update_cli.py" verify $demo.FullName --public "$install\updates_demo\keys\signing-public.pem" --master "$install\updates_demo\keys\master.key" 2>&1
    Check "update_verify" ($LASTEXITCODE -eq 0) ($verify | Select-Object -Last 1)
  } catch { Check "update_verify" $false $_.Exception.Message }
}

try {
  if (Test-Path $install) {
    New-Item -ItemType Directory -Force -Path (Join-Path $install "data") | Out-Null
    "keep-me" | Set-Content (Join-Path $install "data\marker.txt")
    $env:RU_NONINTERACTIVE = "1"
    $env:RU_SKIP_VERIFY = "1"
    $again = cmd.exe /c "`"$src\Setup.cmd`"" 2>&1
    Check "upgrade_exit" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"
    Check "upgrade_data" ((Get-Content (Join-Path $install "data\marker.txt") -ErrorAction SilentlyContinue) -eq "keep-me") ""
  }
} catch { Check "upgrade" $false $_.Exception.Message }

Save-Result
try { Stop-Transcript | Out-Null } catch {}
Write-Host ""
Write-Host "Result: $WorkDir\second_pc_result.json"
Write-Host "Log:    $WorkDir\test.log"
Write-Host "Uninstall is not automated. Use the Start Menu shortcut."
exit 0


