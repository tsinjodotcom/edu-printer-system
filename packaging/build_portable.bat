@echo off
echo ========================================
echo Building Portable Windows Executable (x64)
echo ========================================
echo.

REM Run from the project root, whatever folder this script is started from
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Step 1: Creating build virtual environment...
if exist venv_build rmdir /s /q venv_build
python -m venv venv_build
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv_build\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip

echo Step 4: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Step 5: Building portable executable with PyInstaller...
echo (This may take a few minutes...)
pyinstaller packaging\portable_exe.spec --clean --noconfirm --workpath .pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Portable executable location: dist\EduPrinterSystem.exe
echo.
echo You can now:
echo   - Copy EduPrinterSystem.exe anywhere
echo   - Double-click it to edit the settings and install the service
echo.
echo Settings are saved in config.json next to the exe (default port: 5050)
echo.
pause

