@echo off
setlocal
cd /d "%~dp0"

echo Team Code Link
echo Leave this window open. The live link prints below.
echo Other computers open that link in a browser and log in.
echo.

set "ROOM=%~dp0scripts\workspace.py"
set "PY="

where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3.9 or newer is required.
  echo Install it from https://www.python.org/downloads/
  echo and turn on "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Python 3.9 or newer is required. This computer has an older Python.
  echo.
  pause
  exit /b 1
)

%PY% "%ROOM%" serve %*
echo.
echo The live room stopped.
pause
endlocal
