"""Edu Printer System: one executable, several modes.

    EduPrinterSystem.exe            settings and service window
    EduPrinterSystem.exe serve      print server (what the service runs)
    EduPrinterSystem.exe install    install and start the service
    EduPrinterSystem.exe uninstall  stop and remove the service
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request
from flask_cors import CORS

import config
from printer import pos_print, usb_backend_name

LOG_FILENAME = "service.log"


def create_app(settings: dict) -> Flask:
    flask_app = Flask(__name__)
    CORS(flask_app, origins=[settings["frontendUrl"]])

    @flask_app.route("/", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "usbBackend": usb_backend_name()}), 200

    @flask_app.route("/print", methods=["POST"])
    def print_invoice():
        invoice_data = request.get_json()
        pos_print(invoice_data)
        return "", 204

    return flask_app


def setup_logging() -> None:
    """Send everything to service.log next to the exe.

    The exe is built without a console, so under the service there may be
    no stdout/stderr at all; the log file is the only reliable record.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))

    handler = RotatingFileHandler(
        os.path.join(config.app_dir(), LOG_FILENAME),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def serve() -> None:
    setup_logging()
    log = logging.getLogger("edu_printer")
    try:
        settings = config.load()
        log.info("Starting on port %s, config: %s", settings["port"], config.config_path())
        create_app(settings).run(
            debug=False, host="0.0.0.0", port=settings["port"], use_reloader=False
        )
    except Exception:
        log.exception("The print server stopped on an error")
        raise


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else "gui"

    if command == "gui":
        import gui

        gui.run()
        return 0
    if command == "serve":
        serve()
        return 0
    if command in ("install", "uninstall"):
        import service_manager

        try:
            getattr(service_manager, command)()
        except service_manager.ServiceError as error:
            print(error, file=sys.stderr)
            return 1
        return 0

    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
