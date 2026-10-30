@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if exist "%~dp0Team Code Link.exe" (
  start "" "%~dp0Team Code Link.exe" %*
  exit /b 0
)
if exist "%~dp0dist\Team Code Link.exe" (
  start "" "%~dp0dist\Team Code Link.exe" %*
  exit /b 0
)
title Team Code Link

echo Team Code Link
echo This computer is the host. Leave this window open.
echo.
echo Other computers open the share link this window prints.
echo They can be anywhere. They do not need your Wi-Fi.
echo For this Wi-Fi only, run: launch.bat --local
echo.

set "ROOM=%~dp0scripts\workspace.py"
set "PY="
set "MODE=internet"
set "PORT=8765"
set "HAS_PUBLIC=0"
set "PUBLIC_URL="
set "SERVE_ARGS="

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

:collect_args
if "%~1"=="" goto args_done
if /I "%~1"=="--local" (
  set "MODE=local"
  shift
  goto collect_args
)
if /I "%~1"=="--port" (
  if "%~2"=="" goto bad_args
  set "PORT=%~2"
  call :add_arg --port
  call :add_arg "%~2"
  shift
  shift
  goto collect_args
)
if /I "%~1"=="--public-url" (
  if "%~2"=="" goto bad_args
  set "HAS_PUBLIC=1"
  call :add_arg --public-url
  call :add_arg "%~2"
  shift
  shift
  goto collect_args
)
call :add_arg "%~1"
shift
goto collect_args

:args_done
if "%HAS_PUBLIC%"=="1" goto run_room
if "%MODE%"=="local" (
  echo Starting for this Wi-Fi only.
  echo Other computers must be on this network and open the link below.
  echo.
  call :kill_tunnel
  goto run_room
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open_tunnel.ps1" -Port %PORT%
if errorlevel 1 (
  echo.
  echo The internet link did not start. The room was not opened.
  echo.
  pause
  exit /b 1
)
set "PUBLIC_URL="
set /p PUBLIC_URL=<"%TEMP%\team-code-link-tunnel.url"
if not defined PUBLIC_URL (
  echo The tunnel did not return a public address.
  echo.
  pause
  exit /b 1
)
set SERVE_ARGS=--public-url "%PUBLIC_URL%" %SERVE_ARGS%
echo.
echo Send everyone the line that starts with "Share this link".
echo Closing this window stops the room and that link.
echo.

:run_room
call :start_attach
%PY% "%ROOM%" serve %SERVE_ARGS%
set "SERVE_CODE=%ERRORLEVEL%"
call :kill_tunnel
call :kill_attach
echo.
echo The live room stopped.
pause
exit /b %SERVE_CODE%

:bad_args
echo Usage: launch.bat [--local] [--public-url https://your-tunnel] [--port 8765]
echo.
pause
exit /b 1

:add_arg
set SERVE_ARGS=%SERVE_ARGS% "%~1"
exit /b 0

:kill_tunnel
if not exist "%TEMP%\team-code-link-tunnel.pid" exit /b 0
set "TUNNEL_PID="
set /p TUNNEL_PID=<"%TEMP%\team-code-link-tunnel.pid"
if defined TUNNEL_PID taskkill /PID %TUNNEL_PID% /F >nul 2>&1
del /f /q "%TEMP%\team-code-link-tunnel.pid" >nul 2>&1
del /f /q "%TEMP%\team-code-link-tunnel.url" >nul 2>&1
exit /b 0

:start_attach
call :kill_attach
start "team-link-attach" /MIN %PY% "%~dp0scripts\attach.py"
exit /b 0

:kill_attach
if not exist "%TEMP%\team-code-link-attach.pid" exit /b 0
set "ATTACH_PID="
set /p ATTACH_PID=<"%TEMP%\team-code-link-attach.pid"
if defined ATTACH_PID taskkill /PID %ATTACH_PID% /F >nul 2>&1
del /f /q "%TEMP%\team-code-link-attach.pid" >nul 2>&1
exit /b 0
