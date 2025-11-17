# Installing as Windows Service

This guide explains how to install the portable `.exe` as a Windows service that starts automatically on boot.

## Method 1: Using NSSM (Recommended - Easiest)

NSSM (Non-Sucking Service Manager) can convert any executable into a Windows service.

### Step 1: Download NSSM

1. Download NSSM from: https://nssm.cc/download
2. Extract the ZIP file
3. Copy `nssm.exe` (from the `win64` folder) to one of these locations:
   - **Option A**: Place `nssm.exe` in the same folder as `install_service.bat`
   - **Option B**: Add NSSM to your system PATH

### Step 2: Build the Executable

Make sure you have built the executable:
```batch
build_portable.bat
```

### Step 3: Install the Service

1. **Right-click** `install_service.bat`
2. Select **"Run as administrator"**
3. The script will:
   - Install the service
   - Configure it to start automatically on boot
   - Set up logging

### Step 4: Start the Service

The service is installed but not started. Start it with:
```batch
net start EduPrinterService
```

Or use Services Manager:
- Press `Win + R`, type `services.msc`
- Find "Edu Printer System Service"
- Right-click → Start

### Uninstalling the Service

1. **Right-click** `uninstall_service.bat`
2. Select **"Run as administrator"**
3. The service will be stopped and removed

## Method 2: Manual NSSM Installation

If you prefer to install manually:

```batch
REM Install (run as Administrator)
nssm install EduPrinterService "C:\path\to\EduPrinterSystem.exe"

REM Configure
nssm set EduPrinterService DisplayName "Edu Printer System Service"
nssm set EduPrinterService Description "Invoice printing service"
nssm set EduPrinterService Start SERVICE_AUTO_START
nssm set EduPrinterService AppDirectory "C:\path\to\dist"

REM Start
net start EduPrinterService

REM Stop
net stop EduPrinterService

REM Uninstall
nssm remove EduPrinterService confirm
```

## Service Management

### Using Command Line:
```batch
net start EduPrinterService      # Start
net stop EduPrinterService       # Stop
net restart EduPrinterService    # Restart (if supported)
```

### Using Services Manager:
1. Press `Win + R`
2. Type `services.msc`
3. Find "Edu Printer System Service"
4. Right-click for options (Start, Stop, Restart, Properties)

### Using NSSM GUI:
```batch
nssm edit EduPrinterService
```
This opens a GUI to configure the service.

## Service Configuration

The service is configured to:
- **Start automatically** on boot
- **Run in the background** (no console window)
- **Log output** to `dist\service.log` and `dist\service_error.log`
- **Use the same directory** as the exe for `.env` file

## Troubleshooting

### Service won't start:
1. Check Windows Event Viewer for errors
2. Check `dist\service_error.log` for error messages
3. Verify the `.exe` path is correct
4. Ensure the `.env` file exists in the `dist` folder (if needed)

### Service starts but API doesn't work:
1. Check `dist\service.log` for startup messages
2. Verify the port isn't already in use
3. Check Windows Firewall settings

### Can't install service:
1. Ensure you're running as Administrator
2. Verify NSSM is in PATH or in the same folder
3. Check if the service name already exists

### Service stops unexpectedly:
1. Check `dist\service_error.log` for crash logs
2. Verify printer is connected (if required)
3. Check Windows Event Viewer for system errors

## Logs Location

Service logs are saved in:
- `dist\service.log` - Standard output
- `dist\service_error.log` - Error output

## Notes

- The service runs with the same permissions as the SYSTEM account
- USB printer access may require additional permissions
- The service starts automatically on boot
- No console window will appear when running as a service
- Configuration is read from `.env` file in the `dist` folder

