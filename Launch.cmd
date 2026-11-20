@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "RU_WORKSPACE=%CD%"
set "RU_WORK=%CD%\data"
set "RU_PYTHON=%CD%\runtime\python\python.exe"
set "RU_NODE=%CD%\runtime\node\node.exe"
set "JAVA_HOME=%CD%\tools\jdk21"
set "GHIDRA_INSTALL_DIR=%CD%\tools\ghidra_12.1.4_PUBLIC"
set "PATH=%CD%\runtime\node;%CD%\tools\rea-runtime\node_modules\.bin;%PATH%"
set "PORT=8765"

if not exist "%RU_PYTHON%" (
  echo ERROR: runtime\python\python.exe is missing.
  echo Re-extract the package or run Setup.cmd again.
  pause
  exit /b 1
)
if not exist "%CD%\studio\server.py" (
  echo ERROR: studio\server.py is missing.
  echo Re-extract the package or run Setup.cmd again.
  pause
  exit /b 1
)
if not exist "%CD%\data\logs" mkdir "%CD%\data\logs" >nul 2>nul
set "LOG=%CD%\data\logs\server.log"

netstat -ano | findstr /R /C:":8765 .*LISTENING" >nul
if not errorlevel 1 (
  curl -s --max-time 2 http://127.0.0.1:8765/api/status | findstr /C:"Reverse Update Studio" >nul
  if not errorlevel 1 goto open
  set "PORT=8766"
)

start "" /min cmd /c ""%RU_PYTHON%" "%CD%\studio\server.py" --host 127.0.0.1 --port %PORT% > "%LOG%" 2>&1"

for /l %%i in (1,1,30) do (
  curl -s --max-time 2 http://127.0.0.1:%PORT%/api/status | findstr /C:"Reverse Update Studio" >nul
  if not errorlevel 1 goto open
  timeout /t 1 /nobreak >nul
)

echo.
echo Reverse Update Studio did not start.
echo Log: %LOG%
echo.
type "%LOG%" 2>nul
pause
exit /b 1

:open
set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if defined EDGE (
  start "" "%EDGE%" --app=http://127.0.0.1:%PORT%/ --window-size=1440,1000
) else (
  start "" "http://127.0.0.1:%PORT%/"
)
endlocal
