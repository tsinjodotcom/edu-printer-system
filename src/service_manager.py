"""Install, remove and control the Windows service.

The service is the same executable started with the `serve` argument, hosted
by NSSM. NSSM is bundled inside the exe and copied next to it on install,
because Windows keeps running it for as long as the service exists.
"""
import os
import shutil
import subprocess
import sys
from typing import List

from config import app_dir, is_frozen

SERVICE_NAME = "EduPrinterService"
DISPLAY_NAME = "Edu Printer System Service"
DESCRIPTION = "Invoice printing service for education system"
NSSM_FILENAME = "nssm.exe"

NOT_INSTALLED = "not_installed"
STOPPED = "stopped"
RUNNING = "running"
PENDING = "pending"

ERROR_SERVICE_DOES_NOT_EXIST = 1060


class ServiceError(Exception):
    """A service operation failed; the message is fit to show the user."""


def is_supported() -> bool:
    return sys.platform == "win32"


def _require_windows() -> None:
    if not is_supported():
        raise ServiceError("The service can only be managed on Windows.")


def status() -> str:
    """One of NOT_INSTALLED, STOPPED, RUNNING, PENDING."""
    _require_windows()
    import pywintypes
    import win32service
    import win32serviceutil

    try:
        state = win32serviceutil.QueryServiceStatus(SERVICE_NAME)[1]
    except pywintypes.error as error:
        if error.winerror == ERROR_SERVICE_DOES_NOT_EXIST:
            return NOT_INSTALLED
        raise ServiceError(f"Cannot read the service status: {error.strerror}") from error
    if state == win32service.SERVICE_RUNNING:
        return RUNNING
    if state == win32service.SERVICE_STOPPED:
        return STOPPED
    return PENDING


def serve_command() -> List[str]:
    """Command line the service runs."""
    if is_frozen():
        return [os.path.abspath(sys.executable), "serve"]
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return [os.path.abspath(sys.executable), main_script, "serve"]


def bundled_nssm_path() -> str:
    if is_frozen():
        return os.path.join(sys._MEIPASS, NSSM_FILENAME)
    return os.path.join(app_dir(), "vendor", "nssm-2.24", "win64", NSSM_FILENAME)


def installed_nssm_path() -> str:
    return os.path.join(app_dir(), NSSM_FILENAME)


def _ensure_nssm() -> str:
    """Path of the NSSM copy next to the exe, created if missing."""
    target = installed_nssm_path()
    if not os.path.isfile(target):
        source = bundled_nssm_path()
        if not os.path.isfile(source):
            raise ServiceError(f"The bundled service manager is missing: {source}")
        try:
            shutil.copyfile(source, target)
        except OSError as error:
            raise ServiceError(f"Cannot write {target}: {error}") from error
    return target


def _decode(output: bytes) -> str:
    # NSSM writes UTF-16 when its output is piped.
    encoding = "utf-16-le" if b"\x00" in output else "utf-8"
    return output.decode(encoding, errors="replace").strip()


def _nssm(*args: str, check: bool = True) -> int:
    command = [_ensure_nssm(), *args]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if check and result.returncode != 0:
        detail = _decode(result.stdout) or f"exit code {result.returncode}"
        raise ServiceError(f"nssm {' '.join(args[:2])} failed: {detail}")
    return result.returncode


def start() -> None:
    _require_windows()
    _nssm("start", SERVICE_NAME)


def stop() -> None:
    _require_windows()
    if status() != STOPPED:
        _nssm("stop", SERVICE_NAME)


def restart() -> None:
    _require_windows()
    _nssm("restart", SERVICE_NAME)


def install() -> None:
    """Register the service to start on boot, and start it now.

    An existing installation is replaced, so this also repairs a service
    that points at an exe which has since been moved.
    """
    _require_windows()
    if status() != NOT_INSTALLED:
        uninstall(remove_nssm=False)

    _nssm("install", SERVICE_NAME, *serve_command())
    _nssm("set", SERVICE_NAME, "DisplayName", DISPLAY_NAME)
    _nssm("set", SERVICE_NAME, "Description", DESCRIPTION)
    _nssm("set", SERVICE_NAME, "Start", "SERVICE_AUTO_START")
    _nssm("set", SERVICE_NAME, "AppDirectory", app_dir())
    start()


def uninstall(remove_nssm: bool = True) -> None:
    """Stop and remove the service. Does nothing if it is not installed."""
    _require_windows()
    if status() != NOT_INSTALLED:
        _nssm("stop", SERVICE_NAME, check=False)
        _nssm("remove", SERVICE_NAME, "confirm")
    if remove_nssm:
        try:
            os.remove(installed_nssm_path())
        except OSError:
            # Still locked by the stopping service, or already gone: harmless.
            pass
