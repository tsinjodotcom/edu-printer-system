@echo off
echo ========================================
echo Install Edu Printer System as Service
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

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set EXE_PATH=%SCRIPT_DIR%dist\EduPrinterSystem.exe

REM Check if exe exists
if not exist "%EXE_PATH%" (
    echo ERROR: EduPrinterSystem.exe not found at: %EXE_PATH%
    echo Please build the executable first using build_portable.bat
    pause
    exit /b 1
)

echo Installing service...
echo Service Name: EduPrinterService
echo Executable: %EXE_PATH%
echo.

REM Install the service
nssm install EduPrinterService "%EXE_PATH%"

if %errorLevel% neq 0 (
    echo ERROR: Failed to install service
    pause
    exit /b 1
)

REM Configure service
echo Configuring service...
nssm set EduPrinterService DisplayName "Edu Printer System Service"
nssm set EduPrinterService Description "Invoice printing service for education system"
nssm set EduPrinterService Start SERVICE_AUTO_START
nssm set EduPrinterService AppDirectory "%SCRIPT_DIR%dist"
nssm set EduPrinterService AppStdout "%SCRIPT_DIR%dist\service.log"
nssm set EduPrinterService AppStderr "%SCRIPT_DIR%dist\service_error.log"

echo.
echo Service installed successfully!
echo.
echo To start the service:
echo   net start EduPrinterService
echo.
echo To stop the service:
echo   net stop EduPrinterService
echo.
echo To uninstall the service:
echo   Run uninstall_service.bat
echo.
pause

