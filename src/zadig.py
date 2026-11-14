"""Open Zadig, the tool that installs the printer's USB driver.

A copy already on the PC is preferred; otherwise the one bundled inside the
exe is used, so nothing has to be downloaded.
"""
import glob
import os
import shutil
import sys
import tempfile
from typing import Optional, Tuple

from config import app_dir, is_frozen

BUNDLED_FILENAME = "zadig.exe"
BUNDLED_VERSION = "2.9"


class ZadigError(Exception):
    """Zadig could not be started; the message is fit to show the user."""


def is_supported() -> bool:
    return sys.platform == "win32"


def find_existing() -> Optional[str]:
    """A Zadig the PC already has: next to our exe, or on the PATH (where
    winget, Chocolatey and Scoop put it)."""
    beside = sorted(glob.glob(os.path.join(app_dir(), "zadig*.exe")))
    if beside:
        return beside[-1]
    return shutil.which("zadig")


def bundled_path() -> str:
    if is_frozen():
        return os.path.join(sys._MEIPASS, BUNDLED_FILENAME)
    return os.path.join(app_dir(), "vendor", "zadig", BUNDLED_FILENAME)


def extract_bundled() -> str:
    """Copy the bundled Zadig out of the exe and return the copy's path.

    The bundle is unpacked in a folder that is deleted when our window
    closes; Zadig must be able to outlive it.
    """
    source = bundled_path()
    if not os.path.isfile(source):
        raise ZadigError(f"The bundled Zadig is missing: {source}")
    folder = os.path.join(tempfile.gettempdir(), "EduPrinterSystem")
    target = os.path.join(folder, f"zadig-{BUNDLED_VERSION}.exe")
    try:
        os.makedirs(folder, exist_ok=True)
        if not os.path.isfile(target) or os.path.getsize(target) != os.path.getsize(source):
            shutil.copyfile(source, target)
    except OSError as error:
        raise ZadigError(f"Cannot prepare Zadig in {folder}: {error}") from error
    return target


def locate() -> Tuple[str, bool]:
    """Path of the Zadig to run, and whether it is the bundled one."""
    existing = find_existing()
    if existing:
        return existing, False
    return extract_bundled(), True


def open_zadig() -> Tuple[str, bool]:
    """Start Zadig without waiting for it. Returns what locate() returned."""
    if not is_supported():
        raise ZadigError("Zadig only runs on Windows.")
    path, bundled = locate()
    try:
        # Through the shell, so Windows shows Zadig's own administrator prompt.
        os.startfile(path)
    except OSError as error:
        raise ZadigError(f"Cannot start {path}: {error}") from error
    return path, bundled
