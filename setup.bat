@echo off
title PDF Toolkit - Setup
color 0A

echo ========================================
echo    PDF Toolkit - Setup Script
echo ========================================
echo.

REM Detect project directory
cd /d "%~dp0"

set "PYEXE="

REM Find a real Python (skips the fake Microsoft Store stub in WindowsApps)
py -3 -c "print('ok')" >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py -3"
    echo [OK] Python launcher found.
    goto :pyok
)
where python >nul 2>&1
if not errorlevel 1 (
    python -c "print('ok')" >nul 2>&1
    if not errorlevel 1 (
        set "PYEXE=python"
        echo [OK] Python found.
        goto :pyok
    )
)
echo [ERROR] No working Python was found.
echo NOTE: The 'python' in WindowsApps is only a Microsoft Store shortcut.
echo.
pause
exit /b 1

:pyok
%PYEXE% --version
echo.

REM Create virtual environment
echo [INFO] Creating virtual environment...
if not exist "venv" (
    %PYEXE% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [INFO] Virtual environment already exists.
)
echo.

REM Install dependencies with the venv Python
echo [INFO] Installing dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.
echo.

REM Create storage directories
echo [INFO] Creating storage directories...
if not exist "storage\uploads" mkdir "storage\uploads"
if not exist "storage\outputs" mkdir "storage\outputs"
echo [OK] Storage directories created.
echo.

echo ========================================
echo    Setup completed successfully!
echo ========================================
echo.
echo To start the application, double-click start.bat
echo or run: venv\Scripts\python.exe backend\main.py
echo.
pause
