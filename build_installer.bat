@echo off
REM Build script for Windows Uninstaller Installer
REM Requires:
REM   1. EXE file to be built first (run build_exe.bat)
REM   2. Inno Setup to be installed: https://jrsoftware.org/isinfo.php

echo ======================================================================
echo Windows Uninstaller - Installer Build Script
echo ======================================================================
echo.

REM Check if EXE exists
if not exist "dist\WindowsUninstaller.exe" (
    echo Error: EXE file not found!
    echo Please build the EXE first with: build_exe.bat
    pause
    exit /b 1
)

REM Check if Inno Setup is installed
set INNO_SETUP="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_SETUP% (
    echo Error: Inno Setup 6 is not installed.
    echo Please download and install from: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

echo [1/2] Building installer with Inno Setup...
%INNO_SETUP% installer.iss

if errorlevel 1 (
    echo.
    echo Error: Inno Setup build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Build complete!
echo.
echo Installer location: Output\WindowsUninstaller-Setup-0.8.0.exe
echo.
pause
