@echo off
echo ========================================
echo Uninstall Edu Printer System Service
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get the directory where this script is located
cd /d "%~dp0"
set SCRIPT_DIR=%CD%
set NSSM_PATH=%SCRIPT_DIR%\nssm.exe

REM Check if NSSM is available
if not exist "%NSSM_PATH%" (
    where nssm >nul 2>&1
    if errorlevel 1 (
        echo NSSM (Non-Sucking Service Manager) is not found.
        echo.
        echo Please download NSSM from: https://nssm.cc/download
        echo Extract nssm.exe from the win64 folder and place it in this folder
        echo.
        pause
        exit /b 1
    )
    set NSSM_CMD=nssm
) else (
    set NSSM_CMD=%NSSM_PATH%
)

echo Stopping service...
net stop EduPrinterService >nul 2>&1

echo Uninstalling service...
"%NSSM_CMD%" remove EduPrinterService confirm

if errorlevel 1 (
    echo ERROR: Failed to uninstall service
    echo The service may not be installed, or there was an error.
    pause
    exit /b 1
)

echo.
echo Service uninstalled successfully!
echo.
pause
