@echo off
echo ========================================
echo Install Edu Printer System as Service
echo ========================================
echo.

echo [LOG] Starting installation script...
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
set EXE_PATH=%SCRIPT_DIR%\EduPrinterSystem.exe
set NSSM_PATH=%SCRIPT_DIR%\nssm.exe

echo [LOG] Script directory: %SCRIPT_DIR%
echo [LOG] Expected EXE path: %EXE_PATH%
echo [LOG] Expected NSSM path: %NSSM_PATH%
echo.

REM Check if exe exists
echo [LOG] Checking if EduPrinterSystem.exe exists...
if not exist "%EXE_PATH%" (
    echo [ERROR] EduPrinterSystem.exe not found at: %EXE_PATH%
    echo [ERROR] Current directory contents:
    dir /b
    echo [ERROR] Please make sure EduPrinterSystem.exe is in the same folder as this script
    pause
    exit /b 1
)
echo [LOG] EduPrinterSystem.exe found successfully
echo.

REM Check if NSSM is available
echo [LOG] Checking for NSSM...
if not exist "%NSSM_PATH%" (
    echo [LOG] NSSM not found in script directory, checking PATH...
    where nssm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] NSSM (Non-Sucking Service Manager) is not found.
        echo [ERROR] Please download NSSM from: https://nssm.cc/download
        echo [ERROR] Extract nssm.exe from the win64 folder and place it in this folder
        echo [ERROR] Current directory: %SCRIPT_DIR%
        pause
        exit /b 1
    )
    echo [LOG] NSSM found in PATH
    set NSSM_CMD=nssm
) else (
    echo [LOG] NSSM found in script directory
    set NSSM_CMD=%NSSM_PATH%
)
echo [LOG] Using NSSM command: %NSSM_CMD%
echo.

REM Check if service already exists
echo [LOG] Checking if service already exists...
sc query EduPrinterService >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Service 'EduPrinterService' already exists
    echo [LOG] Stopping existing service...
    net stop EduPrinterService >nul 2>&1
    echo [LOG] Removing existing service...
    "%NSSM_CMD%" remove EduPrinterService confirm
    if errorlevel 1 (
        echo [ERROR] Failed to remove existing service
        echo [ERROR] You may need to manually remove it using: nssm remove EduPrinterService confirm
        pause
        exit /b 1
    )
    echo [LOG] Existing service removed successfully
    echo.
)

echo [LOG] Installing service...
echo [LOG] Service Name: EduPrinterService
echo [LOG] Executable: %EXE_PATH%
echo [LOG] Working Directory: %SCRIPT_DIR%
echo.

REM Install the service
echo [LOG] Running: "%NSSM_CMD%" install EduPrinterService "%EXE_PATH%"
"%NSSM_CMD%" install EduPrinterService "%EXE_PATH%"
set INSTALL_RESULT=%ERRORLEVEL%

if errorlevel 1 (
    echo [ERROR] Failed to install service
    echo [ERROR] Exit code: %INSTALL_RESULT%
    echo [ERROR] Please check the error message above
    pause
    exit /b 1
)
echo [LOG] Service installed successfully (exit code: %INSTALL_RESULT%)
echo.

REM Configure service
echo [LOG] Configuring service settings...
echo [LOG] Setting DisplayName...
"%NSSM_CMD%" set EduPrinterService DisplayName "Edu Printer System Service"
if errorlevel 1 echo [WARNING] Failed to set DisplayName

echo [LOG] Setting Description...
"%NSSM_CMD%" set EduPrinterService Description "Invoice printing service for education system"
if errorlevel 1 echo [WARNING] Failed to set Description

echo [LOG] Setting Start type to Automatic...
"%NSSM_CMD%" set EduPrinterService Start SERVICE_AUTO_START
if errorlevel 1 echo [WARNING] Failed to set Start type

echo [LOG] Setting Working Directory...
"%NSSM_CMD%" set EduPrinterService AppDirectory "%SCRIPT_DIR%"
if errorlevel 1 echo [WARNING] Failed to set AppDirectory

echo [LOG] Setting stdout log file...
"%NSSM_CMD%" set EduPrinterService AppStdout "%SCRIPT_DIR%\service.log"
if errorlevel 1 echo [WARNING] Failed to set AppStdout

echo [LOG] Setting stderr log file...
"%NSSM_CMD%" set EduPrinterService AppStderr "%SCRIPT_DIR%\service_error.log"
if errorlevel 1 echo [WARNING] Failed to set AppStderr

echo [LOG] Service configuration completed
echo.

REM Verify service installation
echo [LOG] Verifying service installation...
sc query EduPrinterService >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Service verification failed - service may not be installed correctly
    pause
    exit /b 1
)
echo [LOG] Service verified successfully
echo.

echo ========================================
echo [SUCCESS] Service installed successfully!
echo ========================================
echo.
echo Service Details:
echo   Name: EduPrinterService
echo   Display Name: Edu Printer System Service
echo   Executable: %EXE_PATH%
echo   Working Directory: %SCRIPT_DIR%
echo   Log Files: %SCRIPT_DIR%\service.log and service_error.log
echo.
echo Next Steps:
echo   To start the service: net start EduPrinterService
echo   To stop the service: net stop EduPrinterService
echo   To uninstall: Run uninstall_service.bat
echo   To view logs: Check %SCRIPT_DIR%\service.log
echo.
pause
