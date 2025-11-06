@echo off
REM Build script for Windows Uninstaller EXE
REM Requires PyInstaller to be installed: pip install pyinstaller

echo ======================================================================
echo Windows Uninstaller - EXE Build Script
echo ======================================================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Error: PyInstaller is not installed.
    echo Please install it with: pip install pyinstaller
    pause
    exit /b 1
)

echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [2/3] Building EXE with PyInstaller...
pyinstaller windows-uninstaller.spec

if errorlevel 1 (
    echo.
    echo Error: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo EXE file location: dist\WindowsUninstaller.exe
echo.
echo To create an installer, run: build_installer.bat
echo.
pause
