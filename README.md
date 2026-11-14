# Edu Printer System

A small local HTTP service that prints school invoices on a USB thermal (ESC/POS) receipt printer. A web frontend sends the invoice as JSON to `POST /print`; the service formats it for 32-character paper and prints two copies.

It runs on Windows x64 as a single executable, `EduPrinterSystem.exe`. Double-clicking it opens a window to edit the settings and to install it as a Windows service; no other file needs to be copied.

## Download

[`standalone-x64/EduPrinterSystem.exe`](standalone-x64/EduPrinterSystem.exe)

Windows SmartScreen warns about the exe because it is unsigned: choose "More info", then "Run anyway". It asks for administrator rights, which installing a service requires.

## Setup on the printing PC

1. Plug in the printer and install the libusbK driver for it with [Zadig](https://zadig.akeo.ie/).
2. Find the printer's vendor and product IDs (for example with [USBDeview](https://www.nirsoft.net/utils/usb_devices_view.html)).
3. Copy `EduPrinterSystem.exe` to a permanent folder, such as `C:\EduPrinterSystem`, and double-click it.
4. Fill in the configuration and click **Save**.
5. Click **Install service**. The service starts now and on every boot.
6. Open `http://localhost:5050/`. It should answer `{"status": "healthy", "usbBackend": "..."}`.

To update, stop the service, replace the exe, and start the service again. If the exe is moved to another folder, click **Reinstall service**.

More detail: [docs/service-install.md](docs/service-install.md).

## Configuration

Settings live in `config.json`, in the same folder as the exe. The window creates the file on the first **Save**; it can also be edited by hand.

```json
{
  "port": 5050,
  "frontendUrl": "http://localhost:3000",
  "printerVendorId": "0x28E9",
  "printerProductId": "0x0289",
  "schoolName": "INSTITUTION MARTHE HERVEE",
  "schoolPhone": "+261 034 08 040 83",
  "invoiceFooter": "Jesus, mon maitre souverain."
}
```

| Setting | Effect |
|---|---|
| `port` | Port the service listens on. |
| `frontendUrl` | Origin allowed to call the service (CORS). |
| `printerVendorId`, `printerProductId` | USB IDs of the printer, in hexadecimal. |
| `schoolName` | First line of the invoice, printed in capitals. |
| `schoolPhone` | Second line of the invoice. |
| `invoiceFooter` | Last line of the invoice. Leave it empty to print none. |

A setting missing from the file takes the value shown above. Printer and invoice settings apply to the next print. `port` and `frontendUrl` apply when the service restarts, which the window does on Save.

Versions before `config.json` used a `.env` file. If one is still next to the exe and there is no `config.json` yet, its values are used and shown in the window; Save then writes them to `config.json`.

The service writes its log to `service.log` in the same folder.

## API

| Request | Response |
|---|---|
| `GET /` | `200` with the service status and the USB backend in use. |
| `POST /print` | `204` once the invoice has been sent to the printer, `500` if printing failed. |

`POST /print` takes a JSON body:

```json
{
  "invoiceNumber": "F-2026-0412",
  "clientName": "RAKOTO Jean",
  "paidDate": "2026-11-14T10:30:00",
  "elements": [
    { "description": "Ecolage novembre", "amount": 150000 },
    { "description": "Cantine", "amount": 40000 }
  ]
}
```

Amounts above 999 999 are printed in millions (`1 500 000` becomes `1,5M`).

## Project layout

```
src/              Application code
  main.py           Entry point: window, print server, or service install
  gui.py            Settings and service window
  config.py         Reading, validating and writing config.json
  service_manager.py  Installing and controlling the Windows service
  printer.py        Invoice formatting and USB printing
tests/            Unit tests
packaging/        PyInstaller spec and hooks, build script
docs/             Build and installation guides
standalone-x64/   Released exe for Windows x64
vendor/           Third-party binary bundled into the exe (NSSM 2.24)
.github/          CI workflow that tests and builds the Windows exe
```

## Development

```
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt  # pywin32 installs on Windows only
python src/main.py               # settings window
python src/main.py serve         # print server
python -m unittest -v
```

The exe accepts the same arguments, plus `install` and `uninstall` to manage the service without the window. When run from source, `config.json` is read from the project root.

## Building

The exe can only be built on Windows. Every push to `main` runs the tests and builds it on GitHub Actions; the result is the `EduPrinterSystem-windows-x64` artifact of the workflow run.

To build on a Windows machine, run `packaging\build_portable.bat`, which writes `dist\EduPrinterSystem.exe`.

- [docs/portable-exe.md](docs/portable-exe.md): the portable exe
- [docs/service-install.md](docs/service-install.md): installing it as a service
