@echo off
setlocal EnableExtensions
set "INTERACTIVE=1"
if defined RU_NONINTERACTIVE set "INTERACTIVE=0"
title Reverse Update Studio Setup
set "SRC=%~dp0"
set "CANON=%LOCALAPPDATA%\ReverseUpdateStudio"
set "TARGET=%CANON%"
if not "%~1"=="" set "TARGET=%~1"

echo.
echo  Reverse Update Studio - Setup
echo  -----------------------------
echo  From: %SRC%
echo  To:   %TARGET%
echo.

if /I "%SRC%"=="%TARGET%\" (
  echo  Already running from the install folder.
  goto shortcuts
)

if not exist "%SRC%tools\setup_install.ps1" (
  echo ERROR: tools\setup_install.ps1 is missing.
if "%INTERACTIVE%"=="1" pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SRC%tools\setup_install.ps1" -Source "%SRC:~0,-1%" -Target "%TARGET%"
if errorlevel 1 (
  echo.
  echo  ERROR: install failed. The previous version was kept.
if "%INTERACTIVE%"=="1" pause
  exit /b 1
)

:shortcuts
if /I not "%TARGET%"=="%CANON%" (
  echo  Custom install folder: skipping Desktop/Start Menu shortcuts.
  goto done
)
if /I "%SRC%"=="%TARGET%\" (
  if exist "%TARGET%\tools\install_shortcuts.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TARGET%\tools\install_shortcuts.ps1" -Target "%TARGET%"
    if errorlevel 1 (
      echo  ERROR: shortcuts could not be created.
if "%INTERACTIVE%"=="1" pause
      exit /b 1
    )
  )
)

:done
echo.
echo  Installed.
if /I "%TARGET%"=="%CANON%" if not defined RU_NO_SHORTCUTS (
  echo  Desktop:    Reverse Update Studio
  echo  Start Menu: Reverse Update Studio
)
echo.
if "%INTERACTIVE%"=="0" exit /b 0
choice /c YN /n /m "Start Reverse Update Studio now? [Y/N] "
if errorlevel 2 exit /b 0
start "" "%TARGET%\Launch.cmd"
exit /b 0


