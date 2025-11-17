@echo off
echo ========================================
echo Uninstall Edu Printer System Service
echo ========================================
echo.

echo [LOG] Starting uninstall script...
echo [LOG] Script location: %~f0
echo.

REM Check if running as administrator
echo [LOG] Checking for administrator privileges...
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must be run as Administrator
    echo [ERROR] Right-click and select "Run as administrator"
    pause
    exit /b 1
)
echo [LOG] Administrator privileges confirmed
echo.

REM Get the directory where this script is located
echo [LOG] Getting script directory...
cd /d "%~dp0"
set SCRIPT_DIR=%CD%
set NSSM_PATH=%SCRIPT_DIR%\nssm.exe

echo [LOG] Script directory: %SCRIPT_DIR%
echo [LOG] Expected NSSM path: %NSSM_PATH%
echo.

REM Check if NSSM is available
echo [LOG] Checking for NSSM...
if not exist "%NSSM_PATH%" (
    echo [ERROR] NSSM (Non-Sucking Service Manager) is not found.
    echo [ERROR] Expected location: %NSSM_PATH%
    echo [ERROR] Please make sure nssm.exe is in the same folder as this script
    echo [ERROR] Current directory contents:
    dir /b
    pause
    exit /b 1
)
echo [LOG] NSSM found successfully
set NSSM_CMD=%NSSM_PATH%
echo [LOG] Using NSSM command: %NSSM_CMD%
echo.

REM Check if service exists
echo [LOG] Checking if service exists...
sc query EduPrinterService >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Service 'EduPrinterService' does not exist or is not installed
    echo [LOG] Nothing to uninstall
    pause
    exit /b 0
)
echo [LOG] Service found
echo.

REM Stop the service
echo [LOG] Stopping service...
net stop EduPrinterService >nul 2>&1
set STOP_RESULT=%ERRORLEVEL%
if errorlevel 1 (
    echo [WARNING] Service stop command returned error (may already be stopped)
    echo [LOG] Exit code: %STOP_RESULT%
) else (
    echo [LOG] Service stopped successfully
)
echo.

REM Uninstall the service
echo [LOG] Uninstalling service...
echo [LOG] Running: "%NSSM_CMD%" remove EduPrinterService confirm
"%NSSM_CMD%" remove EduPrinterService confirm
set REMOVE_RESULT=%ERRORLEVEL%

if errorlevel 1 (
    echo [ERROR] Failed to uninstall service
    echo [ERROR] Exit code: %REMOVE_RESULT%
    echo [ERROR] The service may not be installed, or there was an error
    pause
    exit /b 1
)
echo [LOG] Service uninstalled successfully (exit code: %REMOVE_RESULT%)
echo.

REM Verify service removal
echo [LOG] Verifying service removal...
sc query EduPrinterService >nul 2>&1
if errorlevel 1 (
    echo [LOG] Service verification: Service no longer exists (removal confirmed)
) else (
    echo [WARNING] Service still appears to exist after removal
    echo [WARNING] You may need to manually remove it
)
echo.

echo ========================================
echo [SUCCESS] Service uninstalled successfully!
echo ========================================
echo.
echo Service Details:
echo   Name: EduPrinterService
echo   Status: Removed
echo.
pause
