# Building Portable Windows Executable (.exe)

This guide explains how to create a standalone `.exe` file that can be dragged and dropped anywhere.

## Quick Build

1. **Run the build script:**
   ```batch
   packaging\build_portable.bat
   ```

2. **Find your executable:**
   - Location: `dist\EduPrinterSystem.exe`
   - This is a standalone file with all dependencies bundled

3. **Use it anywhere:**
   - Copy `EduPrinterSystem.exe` to any folder
   - Double-click to open the settings window

## What You Get

After building, you'll have a single file: `dist\EduPrinterSystem.exe`. Everything else (Python, libusb, the service manager) is inside it.

## How to Use

### Settings and service
1. Double-click `EduPrinterSystem.exe` and accept the administrator prompt
2. Edit the configuration and click **Save** (this writes `config.json` next to the exe)
3. Click **Install service** to run it in the background on every boot

See [service-install.md](service-install.md).

### Without the service
Run `EduPrinterSystem.exe serve` to start the print server directly. It has no console window; it logs to `service.log` next to the exe and runs until the process is ended. The API is available at `http://localhost:5050`.

## Features

- ✅ **Portable** - No installation needed
- ✅ **Standalone** - All dependencies included
- ✅ **x64** - Built for 64-bit Windows
- ✅ **Settings window** - Edit the configuration and manage the service
- ✅ **Auto-config** - Reads `config.json` in the same folder as the exe

## Requirements

- Windows x64 (64-bit)
- No Python installation needed (everything is bundled)
- Administrator rights may be needed for USB printer access

## Troubleshooting

### "Windows protected your PC" warning
- Click "More info" → "Run anyway"
- This is normal for unsigned executables

### Port already in use
- Change the port in the settings window
- Or stop the application using that port

### Printer not found
- Ensure printer is connected via USB
- Check the printer vendor and product IDs in the settings window
- Look at `service.log` next to the exe for the exact error

### No config.json
- Default values are used until one is saved
- The settings window creates it on Save
