# Quick Start Guide - Windows Service Build

## Quick Build (3 Steps)

1. **Run the build script:**
   ```batch
   packaging\build_windows.bat
   ```

2. **Test the service (optional):**
   ```batch
   dist\EduPrinterService.exe install
   net start EduPrinterService
   ```

3. **Create installer:**
   - Install Inno Setup: https://jrsoftware.org/isinfo.php
   - Open `packaging\installer.iss` in Inno Setup
   - Build → Compile
   - Installer will be in `installer\` folder

## What Gets Created

- `dist\EduPrinterService.exe` - The service executable
- `installer\EduPrinterSystem-Setup-x64.exe` - The installer (after Inno Setup compilation)

## Service Commands

```batch
# Install
dist\EduPrinterService.exe install

# Start
net start EduPrinterService

# Stop
net stop EduPrinterService

# Remove
dist\EduPrinterService.exe remove
```

## Configuration

Edit `.env` file in installation directory after installation:
- Default location: `C:\Program Files\EduPrinterSystem\.env`

## Requirements

- Windows x64
- Python 3.8+ (64-bit)
- Administrator privileges for installation

For detailed instructions, see [build-service.md](build-service.md)

