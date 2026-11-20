@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0runtime\python\python.exe" (
  set "RU_WORKSPACE=%CD%"
  set "RU_WORK=%CD%\data"
  set "RU_PYTHON=%CD%\runtime\python\python.exe"
  set "RU_NODE=%CD%\runtime\node\node.exe"
  set "JAVA_HOME=%CD%\tools\jdk21"
  set "GHIDRA_INSTALL_DIR=%CD%\tools\ghidra_12.1.4_PUBLIC"
  set "PATH=%CD%\runtime\node;%CD%\tools\rea-runtime\node_modules\.bin;%PATH%"
  "%CD%\runtime\python\python.exe" "%CD%\cli.py" %*
) else (
  python "%~dp0cli.py" %*
)
endlocal
