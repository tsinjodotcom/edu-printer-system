# Building Windows Installable Service (x64)

This guide explains how to build a Windows x64 installable service for the Edu Printer System.

## Prerequisites

1. **Python 3.8+** (64-bit) installed on Windows
2. **Inno Setup** (for creating the installer) - Download from: https://jrsoftware.org/isinfo.php
3. All project dependencies

## Build Steps

### Option 1: Automated Build (Recommended)

1. Open Command Prompt as Administrator
2. Navigate to the project directory
3. Run the build script:
   ```batch
   build_windows.bat
   ```
4. The script will:
   - Create a virtual environment
   - Install all dependencies
   - Build the executable using PyInstaller
   - Copy necessary files to the `dist` folder

### Option 2: Manual Build

1. Create and activate a virtual environment:
   ```batch
   python -m venv venv_build
   venv_build\Scripts\activate
   ```

2. Install dependencies:
   ```batch
   pip install -r requirements.txt
   ```

3. Build the executable:
   ```batch
   pyinstaller build_service.spec --clean
   ```

4. Copy additional files:
   ```batch
   copy logo.png dist\
   copy .env dist\  (if exists)
   copy .env.example dist\  (if exists)
   ```

## Testing the Service

Before creating the installer, test the service:

1. **Install the service:**
   ```batch
   dist\EduPrinterService.exe install
   ```

2. **Start the service:**
   ```batch
   net start EduPrinterService
   ```

3. **Check if it's running:**
   - Open Services (services.msc)
   - Look for "Edu Printer System Service"
   - Verify it's running

4. **Test the API:**
   ```batch
   curl http://localhost:5050/
   ```

5. **Stop the service:**
   ```batch
   net stop EduPrinterService
   ```

6. **Remove the service:**
   ```batch
   dist\EduPrinterService.exe remove
   ```

## Creating the Installer

1. **Install Inno Setup** (if not already installed)

2. **Open Inno Setup Compiler**

3. **Open the installer script:**
   - File → Open
   - Select `installer.iss`

4. **Build the installer:**
   - Build → Compile
   - The installer will be created in the `installer` folder as `EduPrinterSystem-Setup-x64.exe`

## Installation

1. Run `EduPrinterSystem-Setup-x64.exe` as Administrator
2. Follow the installation wizard
3. The service will be automatically installed and started
4. Configure the `.env` file in `C:\Program Files\EduPrinterSystem\` if needed

## Service Management

### Using Services Manager:
- Press `Win + R`, type `services.msc`
- Find "Edu Printer System Service"
- Right-click for options (Start, Stop, Restart, Properties)

### Using Command Line:
```batch
net start EduPrinterService
net stop EduPrinterService
net restart EduPrinterService
```

### Using the executable:
```batch
EduPrinterService.exe install
EduPrinterService.exe start
EduPrinterService.exe stop
EduPrinterService.exe remove
```

## Configuration

After installation, edit the `.env` file in the installation directory:
- `C:\Program Files\EduPrinterSystem\.env`

Configuration options:
- `FRONTEND_URL` - Frontend URL for CORS
- `PORT` - Service port (default: 5050)
- `PRINTER_VENDOR_ID` - USB printer vendor ID
- `PRINTER_PRODUCT_ID` - USB printer product ID
- `SCHOOL_NAME` - School name
- `SCHOOL_ADDRESS` - School address
- `SCHOOL_PHONE` - School phone
- `SCHOOL_EMAIL` - School email

After changing the `.env` file, restart the service for changes to take effect.

## Troubleshooting

### Service won't start:
1. Check Windows Event Viewer for errors
2. Verify the `.env` file exists and is valid
3. Check if the port is already in use
4. Ensure the printer is connected (if required)

### Service installs but doesn't run:
1. Check if running as Administrator
2. Verify Python dependencies are included in the build
3. Check Windows Firewall settings

### Build fails:
1. Ensure Python 64-bit is installed
2. Verify all dependencies in requirements.txt are available
3. Check PyInstaller version compatibility

## File Structure After Build

```
project/
├── dist/
│   ├── EduPrinterService.exe  (Main executable)
│   ├── logo.png
│   └── .env (or .env.example)
├── installer/
│   └── EduPrinterSystem-Setup-x64.exe  (Final installer)
└── build/  (Temporary build files)
```

## Notes

- The service runs as a Windows service, so it starts automatically on boot
- The service runs in the background (no console window)
- Logs are written to Windows Event Viewer
- The service requires Administrator privileges to install/uninstall

