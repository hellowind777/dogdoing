@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "DOGDOING_ROUTER=%~dp0hook_router.py"
set "DOGDOING_ERROR=%~dp0hook_router_windows_error.txt"

if not defined DOGDOING_PYTHON goto codex_python
if exist "%DOGDOING_PYTHON%" goto explicit_python
type "%DOGDOING_ERROR%" 1>&2
>&2 echo DOGDOING_PYTHON=%DOGDOING_PYTHON%
exit /b 127

:explicit_python
"%DOGDOING_PYTHON%" "%DOGDOING_ROUTER%" %*
exit /b %errorlevel%

:codex_python
set "DOGDOING_CODEX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%DOGDOING_CODEX_PYTHON%" goto path_python
"%DOGDOING_CODEX_PYTHON%" "%DOGDOING_ROUTER%" %*
exit /b %errorlevel%

:path_python
%SystemRoot%\System32\where.exe python.exe >nul 2>nul
if errorlevel 1 goto path_python3
python.exe "%DOGDOING_ROUTER%" %*
exit /b %errorlevel%

:path_python3
%SystemRoot%\System32\where.exe python3.exe >nul 2>nul
if errorlevel 1 goto launcher_python
python3.exe "%DOGDOING_ROUTER%" %*
exit /b %errorlevel%

:launcher_python
%SystemRoot%\System32\where.exe py.exe >nul 2>nul
if errorlevel 1 goto missing_python
py.exe -3 -c "import sys" >nul 2>nul
if errorlevel 1 goto missing_python
py.exe -3 "%DOGDOING_ROUTER%" %*
exit /b %errorlevel%

:missing_python
type "%DOGDOING_ERROR%" 1>&2
exit /b 127
