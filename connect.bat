@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Team Code Link agent

echo Team Code Link
echo Leave this window open.
echo.
echo Open the share link in a browser and log in.
echo That connects the agent on this computer.
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python3 >nul 2>&1 && set "PY=python3"
)
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3.9 or newer is required.
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0scripts\attach.py"
echo.
pause
endlocal
