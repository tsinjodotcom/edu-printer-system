@echo off
echo ========================================
echo Install Edu Printer System as Service
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
set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%EduPrinterSystem.exe"
set "NSSM_PATH=%SCRIPT_DIR%nssm.exe"

REM Check if exe exists
if not exist "%EXE_PATH%" (
    echo ERROR: EduPrinterSystem.exe not found at: %EXE_PATH%
    echo Please make sure EduPrinterSystem.exe is in the same folder as this script
    pause
    exit /b 1
)

REM Check if NSSM is available (first check local folder, then PATH)
if not exist "%NSSM_PATH%" (
    where nssm >nul 2>&1
    if errorlevel 1 (
        echo NSSM (Non-Sucking Service Manager) is not found.
        echo.
        echo Please download NSSM from: https://nssm.cc/download
        echo Extract nssm.exe from the win64 folder and place it in:
        echo %SCRIPT_DIR%
        echo.
        pause
        exit /b 1
    )
    set "NSSM_CMD=nssm"
) else (
    set "NSSM_CMD=%NSSM_PATH%"
)

echo Installing service...
echo Service Name: EduPrinterService
echo Executable: %EXE_PATH%
echo.

REM Install the service
"%NSSM_CMD%" install EduPrinterService "%EXE_PATH%"

if errorlevel 1 (
    echo ERROR: Failed to install service
    pause
    exit /b 1
)

REM Configure service
echo Configuring service...
"%NSSM_CMD%" set EduPrinterService DisplayName "Edu Printer System Service"
"%NSSM_CMD%" set EduPrinterService Description "Invoice printing service for education system"
"%NSSM_CMD%" set EduPrinterService Start SERVICE_AUTO_START
"%NSSM_CMD%" set EduPrinterService AppDirectory "%SCRIPT_DIR%"
"%NSSM_CMD%" set EduPrinterService AppStdout "%SCRIPT_DIR%service.log"
"%NSSM_CMD%" set EduPrinterService AppStderr "%SCRIPT_DIR%service_error.log"

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

