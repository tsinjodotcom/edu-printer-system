@echo off
echo ========================================
echo Uninstall Edu Printer System Service
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if NSSM is available
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo NSSM (Non-Sucking Service Manager) is not found in PATH.
    echo.
    echo Please download NSSM from: https://nssm.cc/download
    echo Extract nssm.exe and either:
    echo   1. Add it to your PATH, OR
    echo   2. Place nssm.exe in this folder
    echo.
    pause
    exit /b 1
)

echo Stopping service...
net stop EduPrinterService >nul 2>&1

echo Uninstalling service...
nssm remove EduPrinterService confirm

if %errorLevel% neq 0 (
    echo ERROR: Failed to uninstall service
    echo The service may not be installed, or there was an error.
    pause
    exit /b 1
)

echo.
echo Service uninstalled successfully!
echo.
pause

