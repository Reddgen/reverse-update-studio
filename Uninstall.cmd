@echo off
setlocal EnableExtensions
set "TARGET=%~dp0"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
if not exist "%TARGET%\tools\uninstall.ps1" (
  echo ERROR: tools\uninstall.ps1 is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TARGET%\tools\uninstall.ps1" -Target "%TARGET%"
if errorlevel 1 (
  pause
  exit /b 1
)
set "RU_TARGET=%TARGET%"
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Remove-Item -LiteralPath $env:RU_TARGET -Recurse -Force -ErrorAction SilentlyContinue"
exit /b 0
