# Installing as a Windows service

The service is `EduPrinterSystem.exe` itself, run in server mode. It starts on boot, runs in the background, and restarts if it crashes.

## Install

1. Copy `EduPrinterSystem.exe` to a permanent folder, for example `C:\EduPrinterSystem`. The service points at this location, so do not leave the exe in Downloads.
2. Double-click the exe and accept the administrator prompt.
3. Check the configuration and click **Save**.
4. Click **Install service**. The status changes to "Running".

The window can be closed afterwards; the service keeps running.

Installing adds these files next to the exe:

| File | Purpose |
|---|---|
| `config.json` | The settings (created on Save). |
| `nssm.exe` | The service host. Windows runs it for as long as the service is installed. |
| `service.log` | Log of the print server, including printing errors. |

## Start, stop, uninstall

Use the **Start**, **Stop** and **Uninstall service** buttons in the window. Uninstalling stops the service, removes it, and deletes `nssm.exe`. `config.json` and the log are kept.

The service is also visible in `services.msc` as "Edu Printer System Service", and answers to:

```batch
net start EduPrinterService
net stop EduPrinterService
```

## Without the window

From an administrator prompt:

```batch
EduPrinterSystem.exe install
EduPrinterSystem.exe uninstall
```

Both exit with code 0 on success.

## Updating the exe

1. Click **Stop** (or `net stop EduPrinterService`).
2. Replace `EduPrinterSystem.exe` with the new one, in the same folder.
3. Click **Start**.

If the exe moves to another folder, open it from the new location and click **Reinstall service**.

## Upgrading from the version with install_service.bat

Put the new exe in place of the old one, open it, and click **Reinstall service**: this replaces the old service. The old `install_service.bat`, `uninstall_service.bat` and `.env` are no longer used. An existing `.env` is read until you click Save, which writes its values to `config.json`.

## Troubleshooting

### The service does not start or the API does not answer
1. Open `service.log` next to the exe.
2. Check that the port in the configuration is not used by another program.
3. Check the Windows Firewall if the frontend runs on another machine.

### Printing fails
1. `service.log` shows the error for each failed print.
2. "USB device not found": check the printer vendor and product IDs, the cable, and the libusbK driver (Zadig).

### "Access is denied" when installing
The exe must run as administrator. Accept the prompt when it opens.
