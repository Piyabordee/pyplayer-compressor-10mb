@echo off
REM ============================================================
REM PyPlayer Compressor - Complete Build Script
REM Build PyInstaller executable + Inno Setup installer
REM ============================================================

SETLOCAL EnableDelayedExpansion

SET "PROJECT_DIR=C:\Users\snowb4ll\Documents\pyplayer-master"
SET "PYTHON_EXE=python"
SET "INNO_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo ============================================================
echo PyPlayer Compressor - Build Script
echo ============================================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.13+ and add to PATH
    pause
    exit /b 1
)
%PYTHON_EXE% --version

REM Check PyInstaller
echo.
echo [2/5] Checking PyInstaller...
%PYTHON_EXE% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    %PYTHON_EXE% -m pip install pyinstaller>=5.13.0
)

REM Check requirements
echo.
echo [3/5] Checking dependencies...
cd /d "%PROJECT_DIR%"
%PYTHON_EXE% -m pip install -r requirements.txt --quiet

REM Build with PyInstaller
echo.
echo [4/5] Building PyPlayer executable...
cd /d "%PROJECT_DIR%\executable"
%PYTHON_EXE% build.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

REM Check Inno Setup
echo.
echo [5/5] Creating installer...
if not exist "%INNO_COMPILER%" (
    echo ERROR: Inno Setup compiler not found
    echo Expected location: %INNO_COMPILER%
    echo Please install Inno Setup: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

REM Build installer
"%INNO_COMPILER%" "%PROJECT_DIR%\executable\installer.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL!
echo ============================================================
echo Output location:
echo   - PyInstaller build: %PROJECT_DIR%\executable\compiled\
echo   - Installer: %PROJECT_DIR%\executable\installer_output\
echo.
echo Setup file:
dir /b "%PROJECT_DIR%\executable\installer_output\*.exe"
echo.
pause
