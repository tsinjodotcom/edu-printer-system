"""Settings stored in config.json next to the executable."""
import json
import os
import sys
from typing import Any, Dict, Mapping

CONFIG_FILENAME = "config.json"

DEFAULTS: Dict[str, Any] = {
    "port": 5050,
    "frontendUrl": "http://localhost:3000",
    "printerVendorId": "0x28E9",
    "printerProductId": "0x0289",
    # With a cutter each copy is cut off as its own ticket; without one the
    # copies are printed in one strip, separated by a line to tear along.
    "hasCutter": False,
    "copies": 2,
    # Characters per line: 32 on 58 mm paper, 48 (some models 42) on 80 mm.
    "lineWidth": 32,
    "schoolName": "ECOLE EXEMPLE",
    # Address and email are printed under the name only when filled in.
    "schoolAddress": "",
    "schoolPhone": "+261 00 00 000 00",
    "schoolEmail": "",
    "invoiceFooter": "Merci pour votre confiance.",
}

# Settings used to live in a .env file; these are the names they had there.
LEGACY_ENV_NAMES = {
    "port": "PORT",
    "frontendUrl": "FRONTEND_URL",
    "printerVendorId": "PRINTER_VENDOR_ID",
    "printerProductId": "PRINTER_PRODUCT_ID",
    "schoolName": "SCHOOL_NAME",
    "schoolAddress": "SCHOOL_ADDRESS",
    "schoolPhone": "SCHOOL_PHONE",
    "schoolEmail": "SCHOOL_EMAIL",
    "invoiceFooter": "INVOICE_FOOTER",
}

# Shown to the user when a value is rejected.
LABELS = {
    "port": "Port",
    "frontendUrl": "Frontend URL",
    "printerVendorId": "Printer vendor ID",
    "printerProductId": "Printer product ID",
    "hasCutter": "Paper cutter",
    "copies": "Copies per print",
    "lineWidth": "Paper width",
    "schoolName": "School name",
    "schoolAddress": "School address",
    "schoolPhone": "School phone",
    "schoolEmail": "School email",
    "invoiceFooter": "Invoice footer",
}


MAX_COPIES = 5
MIN_LINE_WIDTH = 24
MAX_LINE_WIDTH = 64


class ConfigError(Exception):
    """A setting is invalid or config.json cannot be read."""


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    """Folder holding config.json and the logs: next to the exe, or the
    project root when running from source."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_FILENAME)


def parse_usb_id(value: Any) -> int:
    """USB vendor/product ID written in hexadecimal, with or without 0x."""
    return int(str(value).strip(), 16)


def validate(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Clean settings built from DEFAULTS overlaid with `raw`.

    Unknown keys are dropped. Raises ConfigError naming the first bad value.
    """
    settings = dict(DEFAULTS)
    settings.update({key: raw[key] for key in DEFAULTS if key in raw})

    try:
        port = int(str(settings["port"]).strip())
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise ConfigError(f"{LABELS['port']} must be a number between 1 and 65535.")
    settings["port"] = port

    for key in ("printerVendorId", "printerProductId"):
        try:
            usb_id = parse_usb_id(settings[key])
        except ValueError:
            usb_id = -1
        if not 0 <= usb_id <= 0xFFFF:
            raise ConfigError(
                f"{LABELS[key]} must be a hexadecimal USB ID such as 0x28E9."
            )
        settings[key] = f"0x{usb_id:04X}"

    if not isinstance(settings["hasCutter"], bool):
        raise ConfigError(f"{LABELS['hasCutter']} must be true or false.")

    try:
        copies = int(str(settings["copies"]).strip())
    except ValueError:
        copies = 0
    if not 1 <= copies <= MAX_COPIES:
        raise ConfigError(f"{LABELS['copies']} must be a number between 1 and {MAX_COPIES}.")
    settings["copies"] = copies

    try:
        line_width = int(str(settings["lineWidth"]).strip())
    except ValueError:
        line_width = 0
    if not MIN_LINE_WIDTH <= line_width <= MAX_LINE_WIDTH:
        raise ConfigError(
            f"{LABELS['lineWidth']} must be between {MIN_LINE_WIDTH} and {MAX_LINE_WIDTH} characters."
        )
    settings["lineWidth"] = line_width

    for key in ("frontendUrl", "schoolName", "schoolAddress", "schoolPhone", "schoolEmail", "invoiceFooter"):
        settings[key] = str(settings[key]).strip()
    if not settings["frontendUrl"]:
        raise ConfigError(f"{LABELS['frontendUrl']} is required.")

    return settings


def _read_legacy_env(folder: str) -> Dict[str, Any]:
    """Values from a pre-config.json .env file, so an upgrade keeps them."""
    env_path = os.path.join(folder, ".env")
    if not os.path.isfile(env_path):
        return {}
    from dotenv import dotenv_values

    values = dotenv_values(env_path)
    return {
        key: values[name]
        for key, name in LEGACY_ENV_NAMES.items()
        if values.get(name) is not None
    }


def load() -> Dict[str, Any]:
    """Current settings. Never writes: a missing config.json yields the
    defaults, overlaid with an old .env if one is still there."""
    path = config_path()
    if not os.path.isfile(path):
        return validate(_read_legacy_env(app_dir()))
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as error:
        raise ConfigError(f"Cannot read {path}: {error}") from error
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a JSON object.")
    return validate(raw)


def save(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and write config.json, creating it if needed."""
    settings = validate(raw)
    path = config_path()
    temporary = path + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        # Replace in one step so the service never reads a half-written file.
        os.replace(temporary, path)
    except OSError as error:
        raise ConfigError(f"Cannot write {path}: {error}") from error
    return settings
