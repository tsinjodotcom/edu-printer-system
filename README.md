# Edu Printer System

A small local HTTP service that prints school invoices on a USB thermal (ESC/POS) receipt printer. A web frontend sends the invoice as JSON to `POST /print`; the service formats it for 32-character paper and prints two copies.

It runs on Windows x64 as a single portable executable, optionally installed as a Windows service.

## Download

The ready-to-use bundle is in [`standalone-x64/`](standalone-x64):

| File | Purpose |
|---|---|
| `EduPrinterSystem.exe` | The service. Double-click to run, or install it as a Windows service. |
| `install_service.bat` | Installs the exe as a service that starts on boot (run as administrator). |
| `uninstall_service.bat` | Stops and removes the service. |
| `nssm.exe` | Service manager used by the two scripts. |

Windows SmartScreen warns about the exe because it is unsigned: choose "More info", then "Run anyway".

## Setup on the printing PC

1. Plug in the printer and install the libusbK driver for it with [Zadig](https://zadig.akeo.ie/).
2. Find the printer's vendor and product IDs (for example with [USBDeview](https://www.nirsoft.net/utils/usb_devices_view.html)).
3. Copy the `standalone-x64` files to a folder and create a `.env` file next to the exe (see below).
4. Run `install_service.bat` as administrator, then `net start EduPrinterService`.
5. Open `http://localhost:5050/`. It should answer `{"status": "healthy", "usbBackend": "..."}`.

More detail: [docs/service-install.md](docs/service-install.md).

## Configuration

Settings are read from a `.env` file in the same folder as the exe, at startup. Restart the service after changing it. [`.env.example`](.env.example) is a template.

| Variable | Default | Effect |
|---|---|---|
| `PORT` | `5050` | Port the service listens on. |
| `FRONTEND_URL` | `http://localhost:3000` | Origin allowed to call the service (CORS). |
| `PRINTER_VENDOR_ID` | `0x28E9` | USB vendor ID of the printer. |
| `PRINTER_PRODUCT_ID` | `0x0289` | USB product ID of the printer. |
| `SCHOOL_NAME` | `INSTITUTION MARTHE HERVEE` | First line of the invoice, printed in capitals. |
| `SCHOOL_PHONE` | `+261 034 08 040 83` | Second line of the invoice. |
| `INVOICE_FOOTER` | `Jesus, mon maitre souverain.` | Last line of the invoice. Set it to empty to print none. |

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
  main.py           Flask app and entry point of the portable exe
  printer.py        Invoice formatting and USB printing
  service.py        Entry point of the native Windows service build
tests/            Unit tests
assets/           Files bundled into the exe (logo)
packaging/        PyInstaller specs and hooks, build scripts, Inno Setup script
docs/             Build and installation guides
standalone-x64/   Released bundle for Windows x64
vendor/           Third-party code (NSSM 2.24)
.github/          CI workflow that tests and builds the Windows exe
```

## Development

```
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt  # pywin32 installs on Windows only
python src/main.py
python -m unittest -v
```

When run from source, `.env` is read from the project root.

## Building

The exe can only be built on Windows. Every push to `main` runs the tests and builds it on GitHub Actions; the result is the `EduPrinterSystem-windows-x64` artifact of the workflow run.

To build on a Windows machine, run `packaging\build_portable.bat`, which writes `dist\EduPrinterSystem.exe`.

- [docs/portable-exe.md](docs/portable-exe.md): the portable exe
- [docs/service-install.md](docs/service-install.md): installing it as a service with NSSM
- [docs/build-service.md](docs/build-service.md) and [docs/quick-start.md](docs/quick-start.md): the alternative native service build with an installer
