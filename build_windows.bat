@echo off
echo ========================================
echo Building Windows Service (x64)
echo ========================================
echo.

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

echo Step 5: Building executable with PyInstaller...
pyinstaller build_service.spec --clean
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)

echo Step 6: Copying additional files...
if not exist dist mkdir dist
copy logo.png dist\ >nul 2>&1
if exist .env copy .env dist\ >nul 2>&1
if exist .env.example copy .env.example dist\ >nul 2>&1

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Executable location: dist\EduPrinterService.exe
echo.
echo To test the service:
echo   1. Install: dist\EduPrinterService.exe install
echo   2. Start:   net start EduPrinterService
echo   3. Stop:    net stop EduPrinterService
echo   4. Remove:  dist\EduPrinterService.exe remove
echo.
pause

