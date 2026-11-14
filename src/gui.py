"""Settings and service window, shown when the exe is started without arguments."""
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional

import config
import service_manager

FIELDS = (
    "port",
    "frontendUrl",
    "printerVendorId",
    "printerProductId",
    "schoolName",
    "schoolPhone",
    "invoiceFooter",
)

# Read once when the server starts; the others are read on every print.
RESTART_FIELDS = ("port", "frontendUrl")

STATUS_TEXT = {
    service_manager.NOT_INSTALLED: "Not installed",
    service_manager.STOPPED: "Installed, stopped",
    service_manager.RUNNING: "Running",
    service_manager.PENDING: "Starting or stopping...",
}

REFRESH_MS = 2000


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy = False
        self.service_status: Optional[str] = None
        self.results: "queue.Queue" = queue.Queue()
        self.entries: Dict[str, tk.StringVar] = {}

        root.title("Edu Printer System")
        root.resizable(False, False)
        outer = ttk.Frame(root, padding=12)
        outer.grid(sticky="nsew")

        self._build_service_frame(outer).grid(row=0, column=0, sticky="ew")
        self._build_config_frame(outer).grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.message = tk.StringVar()
        ttk.Label(outer, textvariable=self.message, wraplength=420).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )

        try:
            self.settings = config.load()
        except config.ConfigError as error:
            self.settings = dict(config.DEFAULTS)
            self.message.set(f"{error} Showing the default settings.")
        self.show_settings(self.settings)

        self._after_id: Optional[str] = None
        root.bind("<Destroy>", self._on_destroy)
        self.refresh_status()
        self._poll()

    def _build_service_frame(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Windows service", padding=10)
        self.status_text = tk.StringVar()
        ttk.Label(frame, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.status_text).grid(
            row=0, column=1, columnspan=3, sticky="w", padx=(6, 0)
        )
        self.install_button = ttk.Button(frame, text="Install service", command=self.on_install)
        self.uninstall_button = ttk.Button(frame, text="Uninstall service", command=self.on_uninstall)
        self.start_button = ttk.Button(frame, text="Start", command=self.on_start)
        self.stop_button = ttk.Button(frame, text="Stop", command=self.on_stop)
        buttons = (self.install_button, self.uninstall_button, self.start_button, self.stop_button)
        for column, button in enumerate(buttons):
            button.grid(row=1, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0), pady=(8, 0))
        return frame

    def _build_config_frame(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
        for row, key in enumerate(FIELDS):
            ttk.Label(frame, text=config.LABELS[key] + ":").grid(row=row, column=0, sticky="w", pady=2)
            variable = tk.StringVar()
            ttk.Entry(frame, textvariable=variable, width=44).grid(
                row=row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
            self.entries[key] = variable
        self.config_file_text = tk.StringVar()
        ttk.Label(frame, textvariable=self.config_file_text, wraplength=420).grid(
            row=len(FIELDS), column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.save_button = ttk.Button(frame, text="Save", command=self.on_save)
        self.save_button.grid(row=len(FIELDS) + 1, column=1, sticky="e", pady=(8, 0))
        return frame

    def show_settings(self, settings: Dict) -> None:
        for key in FIELDS:
            self.entries[key].set(str(settings[key]))
        path = config.config_path()
        note = "" if os.path.isfile(path) else " (not created yet, Save creates it)"
        self.config_file_text.set(f"File: {path}{note}")

    def form_values(self) -> Dict[str, str]:
        return {key: variable.get() for key, variable in self.entries.items()}

    # -- configuration -----------------------------------------------------

    def on_save(self) -> None:
        try:
            saved = config.save(self.form_values())
        except config.ConfigError as error:
            messagebox.showerror("Edu Printer System", str(error), parent=self.root)
            return
        needs_restart = any(saved[key] != self.settings[key] for key in RESTART_FIELDS)
        self.settings = saved
        self.show_settings(saved)
        if needs_restart and self.service_status == service_manager.RUNNING:
            self.run_action("Settings saved. Restarting the service...", service_manager.restart,
                            done="Settings saved and service restarted.")
        else:
            self.message.set("Settings saved.")

    # -- service -----------------------------------------------------------

    def on_install(self) -> None:
        self.run_action("Installing the service...", service_manager.install,
                        done="Service installed and started.")

    def on_uninstall(self) -> None:
        if messagebox.askyesno("Edu Printer System", "Stop and remove the service?", parent=self.root):
            self.run_action("Removing the service...", service_manager.uninstall,
                            done="Service removed.")

    def on_start(self) -> None:
        self.run_action("Starting the service...", service_manager.start, done="Service started.")

    def on_stop(self) -> None:
        self.run_action("Stopping the service...", service_manager.stop, done="Service stopped.")

    def run_action(self, progress: str, action: Callable[[], None], done: str) -> None:
        """Run a slow service operation off the UI thread."""
        if self.busy:
            return
        self.busy = True
        self.message.set(progress)
        self.update_buttons()

        def work() -> None:
            try:
                action()
                self.results.put((done, None))
            except Exception as error:  # shown to the user, never fatal
                self.results.put((None, str(error)))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self) -> None:
        """Pick up finished operations and keep the status current."""
        try:
            done, error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.message.set(done or "")
            if error:
                messagebox.showerror("Edu Printer System", error, parent=self.root)
        self.refresh_status()
        self._after_id = self.root.after(REFRESH_MS if not self.busy else 200, self._poll)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self.root and self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def refresh_status(self) -> None:
        if not service_manager.is_supported():
            self.service_status = None
            self.status_text.set("Available on Windows only")
        else:
            try:
                self.service_status = service_manager.status()
                self.status_text.set(STATUS_TEXT[self.service_status])
            except service_manager.ServiceError as error:
                self.service_status = None
                self.status_text.set(str(error))
        self.update_buttons()

    def update_buttons(self) -> None:
        status = self.service_status
        installed = status in (service_manager.STOPPED, service_manager.RUNNING, service_manager.PENDING)
        idle = not self.busy and status is not None

        def enable(button: ttk.Button, condition: bool) -> None:
            button.state(["!disabled"] if condition else ["disabled"])

        self.install_button.configure(text="Reinstall service" if installed else "Install service")
        enable(self.install_button, idle)
        enable(self.uninstall_button, idle and installed)
        enable(self.start_button, idle and status == service_manager.STOPPED)
        enable(self.stop_button, idle and status == service_manager.RUNNING)
        enable(self.save_button, not self.busy)


def run() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
