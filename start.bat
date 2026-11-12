@echo off
title PDF Toolkit
color 0A

echo ========================================
echo    PDF Toolkit - Start Server
echo ========================================
echo.

REM Detect project directory
cd /d "%~dp0"

REM If the server is already running, just open the site instead of
REM failing with a "port already in use" error
netstat -ano | findstr "LISTENING" | findstr ":8010 " >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Server is already running. Opening the site...
    start "" http://127.0.0.1:8010
    echo [INFO] You can close this window.
    timeout /t 3 >nul
    exit /b 0
)

set "PYEXE="

REM 1) Prefer the project's virtual environment
if exist "venv\Scripts\python.exe" (
    set "PYEXE=venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python.
    goto :deps
)

REM 2) Try the real Python launcher (skips the fake Microsoft Store stub)
py -3 -c "print('ok')" >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py -3"
    echo [OK] Python launcher found.
    goto :deps
)

REM 3) Fall back to system python if it actually works
where python >nul 2>&1
if not errorlevel 1 (
    python -c "print('ok')" >nul 2>&1
    if not errorlevel 1 (
        set "PYEXE=python"
        echo [OK] Python found.
        goto :deps
    )
)

echo [ERROR] No working Python was found.
echo NOTE: The 'python' shown in WindowsApps is only a Microsoft Store
echo shortcut, not a real installation. This script needs a real Python.
echo.
pause
exit /b 1

:deps
echo [INFO] Checking dependencies...
%PYEXE% -c "import fastapi, uvicorn, fitz, PIL, pypdf, docx, multipart, aiofiles" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Some packages are missing. Installing them now, please wait...
    %PYEXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        echo Check your internet connection and run setup.bat once.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
) else (
    echo [OK] All dependencies are ready.
)
echo.

echo [OK] Starting PDF Toolkit server...
echo [INFO] URL: http://127.0.0.1:8010  (press Ctrl+C to stop)
echo.

start "" http://127.0.0.1:8010

%PYEXE% backend\main.py

echo.
echo [INFO] Server stopped.
echo.
pause
