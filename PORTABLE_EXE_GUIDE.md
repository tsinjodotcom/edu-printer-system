# Building Portable Windows Executable (.exe)

This guide explains how to create a standalone `.exe` file that can be dragged and dropped anywhere.

## Quick Build

1. **Run the build script:**
   ```batch
   build_portable.bat
   ```

2. **Find your executable:**
   - Location: `dist\EduPrinterSystem.exe`
   - This is a standalone file with all dependencies bundled

3. **Use it anywhere:**
   - Copy `EduPrinterSystem.exe` to any folder
   - Optionally copy `.env` file to the same folder (for configuration)
   - Double-click to run

## What You Get

After building, you'll have:
- `dist\EduPrinterSystem.exe` - The portable executable (all-in-one)
- `dist\logo.png` - Logo file (if needed)
- `dist\.env` or `.env.example` - Configuration file

## How to Use

### Option 1: Simple Run
1. Double-click `EduPrinterSystem.exe`
2. A console window will open showing the server status
3. The API will be available at `http://localhost:5050`
4. Press `Ctrl+C` to stop

### Option 2: With Configuration
1. Copy `EduPrinterSystem.exe` to a folder
2. Copy `.env` file to the same folder (or create one from `.env.example`)
3. Edit `.env` to configure:
   - `PORT` - Server port (default: 5050)
   - `FRONTEND_URL` - Frontend URL for CORS
   - Printer settings
   - School information
4. Double-click `EduPrinterSystem.exe`

## Features

- ✅ **Portable** - No installation needed
- ✅ **Standalone** - All dependencies included
- ✅ **x64** - Built for 64-bit Windows
- ✅ **Console window** - Shows server status and logs
- ✅ **Auto-config** - Finds `.env` file in the same folder as the exe

## Requirements

- Windows x64 (64-bit)
- No Python installation needed (everything is bundled)
- Administrator rights may be needed for USB printer access

## Troubleshooting

### "Windows protected your PC" warning
- Click "More info" → "Run anyway"
- This is normal for unsigned executables

### Port already in use
- Change the `PORT` in `.env` file
- Or stop the application using that port

### Printer not found
- Ensure printer is connected via USB
- Check `PRINTER_VENDOR_ID` and `PRINTER_PRODUCT_ID` in `.env`
- Run as Administrator if needed

### Can't find .env file
- The exe looks for `.env` in the same folder
- Create one from `.env.example` if needed
- Default values will be used if `.env` is missing

## File Structure

```
YourFolder/
├── EduPrinterSystem.exe  (The portable executable)
├── .env                  (Optional - configuration)
└── logo.png              (Optional - if needed)
```

That's it! Just drag and drop the `.exe` anywhere and run it.

