"""Settings and service window, shown when the exe is started without arguments."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Callable, Dict, NamedTuple, Optional

import config
import printer
import service_manager
import zadig

APP_NAME = "Edu Printer System"

# Read once when the server starts; the others are read on every print.
RESTART_FIELDS = ("port", "frontendUrl")

TICK_MS = 250
PROBE_EVERY_MS = 2000

# tone -> (banner background, accent)
TONES = {
    "ok": ("#E6F4EA", "#1E8E3E"),
    "warn": ("#FEF3E0", "#B06000"),
    "bad": ("#FCE8E6", "#C5221F"),
    "idle": ("#F1F3F4", "#5F6368"),
    "busy": ("#E8F0FE", "#1A73E8"),
}
INK = "#202124"
INK_SOFT = "#4A4F55"
HINT = "#6B7280"
PAPER = "#FFFFFF"
ERROR = "#C5221F"

SAMPLE_INVOICE = {
    "invoiceNumber": "F-2026-0412",
    "clientName": "RAKOTO Jean",
    "paidDate": "2026-11-14T10:30:00",
    "payments": [{"methodPaymentId": 2}],
    "elements": [
        {"description": "Ecolage novembre", "amount": 150000},
        {"description": "Frais d'inscription et fournitures", "amount": 1250000},
    ],
}
TEST_INVOICE = dict(SAMPLE_INVOICE, invoiceNumber="TEST", clientName="Ticket de test")
CUT_MARK = "- - - - - - - cut - - - - - - -"


class Probe(NamedTuple):
    """What the PC looks like right now."""

    status: Optional[str]  # a service_manager state, None if unknown
    healthy: Optional[bool]  # the server answers; None if not checked
    printer: Optional[bool]  # the printer is visible on USB; None if unknown
    error: Optional[str] = None


class ServiceView(NamedTuple):
    """How the service state is presented in the banner."""

    tone: str
    title: str
    detail: str
    primary: Optional[str]  # "install", "start", "stop", "restart" or None


def check_health(port: int) -> bool:
    """Whether the print server answers on this PC."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/", timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def probe(settings: Dict) -> Probe:
    """Slow: queries Windows, the server and USB. Run off the UI thread."""
    if not service_manager.is_supported():
        return Probe(None, None, None)
    error = None
    try:
        status: Optional[str] = service_manager.status()
    except service_manager.ServiceError as failure:
        status, error = None, str(failure)
    healthy = check_health(settings["port"]) if status == service_manager.RUNNING else None
    try:
        connected = printer.printer_connected(
            config.parse_usb_id(settings["printerVendorId"]),
            config.parse_usb_id(settings["printerProductId"]),
        )
    except Exception:
        connected = None
    return Probe(status, healthy, connected, error)


def describe_service(result: Probe, port: int, supported: bool = True) -> ServiceView:
    """The banner for a probe result."""
    if not supported:
        return ServiceView("idle", "Service unavailable", "Windows only.", None)
    if result.error:
        return ServiceView("bad", "Service state unknown", result.error, None)
    status = result.status
    if status == service_manager.NOT_INSTALLED:
        return ServiceView(
            "idle", "Service not installed", "", "install",
        )
    if status == service_manager.STOPPED:
        return ServiceView(
            "warn", "Service stopped", "Invoices cannot be printed.", "start",
        )
    if status == service_manager.PENDING:
        return ServiceView("busy", "Service starting or stopping...", "", None)
    if status == service_manager.RUNNING:
        address = f"http://localhost:{port}"
        if result.healthy is False:
            return ServiceView(
                "bad", "Service running, but not answering",
                f"No answer on {address}. See the service log.", "restart",
            )
        return ServiceView("ok", "Service running", address, "stop")
    return ServiceView("idle", "Checking the service...", "", None)


PRIMARY_LABELS = {
    "install": "Install service",
    "start": "Start",
    "stop": "Stop",
    "restart": "Restart",
}


def preview_copies(values: Dict) -> int:
    """Copies to draw: the form's value, kept within what can be saved."""
    try:
        return min(max(int(str(values.get("copies", "")).strip()), 1), config.MAX_COPIES)
    except ValueError:
        return 1


def render_preview(values: Dict) -> str:
    """The paper a print produces with these (possibly unsaved) form values."""
    settings = dict(config.DEFAULTS)
    for key in ("schoolName", "schoolAddress", "schoolPhone", "schoolEmail", "invoiceFooter"):
        settings[key] = str(values.get(key, "")).strip()
    copies = preview_copies(values)
    ticket = printer.generate_invoice_string(SAMPLE_INVOICE, settings, datetime.now())
    if values.get("hasCutter"):
        return "\n".join([ticket, CUT_MARK] * copies)
    separator = "=" * printer.MAX_LINE_WIDTH
    return f"\n{separator}\n".join([ticket] * copies) + f"\n{CUT_MARK}"


def open_path(path: str) -> None:
    """Open a file or folder with the system's default program."""
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy_text: Optional[str] = None
        self.probe_result = Probe(None, None, None)
        self.results: "queue.Queue" = queue.Queue()
        self.entries: Dict[str, tk.Variable] = {}
        self.widgets: Dict[str, tk.Widget] = {}
        self._probing = False
        self._since_probe = PROBE_EVERY_MS
        self._after_id: Optional[str] = None
        self._loading = False

        self._setup_styles()
        root.title(APP_NAME)
        root.resizable(False, False)
        root.columnconfigure(0, weight=1)

        self._build_banner(root).grid(row=0, column=0, sticky="ew")
        body = ttk.Frame(root, padding=(18, 14, 18, 6))
        body.grid(row=1, column=0, sticky="nsew")
        self._build_form(body).grid(row=0, column=0, sticky="nw")
        self._build_preview(body).grid(row=0, column=1, sticky="ne", padx=(22, 0))
        ttk.Separator(root).grid(row=2, column=0, sticky="ew")
        self._build_footer(root).grid(row=3, column=0, sticky="ew")

        notice = ""
        try:
            self.settings = config.load()
        except config.ConfigError as error:
            self.settings = dict(config.DEFAULTS)
            notice = f"{error} Showing the default settings."
        self.show_settings(self.settings)
        if notice:
            self.set_message(notice, error=True)

        root.bind("<Control-s>", lambda event: self.on_save())
        root.bind("<Command-s>", lambda event: self.on_save())
        root.bind("<Destroy>", self._on_destroy)
        self.apply_probe(self._quick_probe())
        self._tick()

    # -- construction ------------------------------------------------------

    def _setup_styles(self) -> None:
        base = tkfont.nametofont("TkDefaultFont")
        size = base.cget("size")
        self.font_title = base.copy()
        self.font_title.configure(size=size + 5 if size > 0 else size - 5, weight="bold")
        self.font_section = base.copy()
        self.font_section.configure(weight="bold")
        self.font_hint = base.copy()
        self.font_hint.configure(size=size - 1 if size > 0 else size + 1)
        self.font_paper = tkfont.nametofont("TkFixedFont").copy()
        style = ttk.Style(self.root)
        style.configure("Section.TLabel", font=self.font_section)
        style.configure("Hint.TLabel", font=self.font_hint, foreground=HINT)
        style.configure("Error.TLabel", foreground=ERROR)

    def _build_banner(self, parent: tk.Widget) -> tk.Frame:
        """Service state, always in view, with the one action that fits it."""
        banner = tk.Frame(parent, padx=18, pady=14)
        banner.columnconfigure(1, weight=1)
        self.banner = banner
        self.dot = tk.Canvas(banner, width=18, height=18, highlightthickness=0)
        self.dot_shape = self.dot.create_oval(2, 2, 16, 16, width=0)
        self.dot.grid(row=0, column=0, padx=(0, 10))
        self.banner_title = tk.Label(banner, font=self.font_title, fg=INK, anchor="w")
        self.banner_title.grid(row=0, column=1, sticky="w")
        self.banner_detail = tk.Label(banner, fg=INK_SOFT, anchor="w", justify="left", wraplength=470)
        self.banner_detail.grid(row=1, column=1, sticky="w")
        self.progress = ttk.Progressbar(banner, mode="indeterminate", length=120)

        actions = tk.Frame(banner)
        actions.grid(row=0, column=2, rowspan=2, sticky="e")
        self.banner_actions = actions
        self.primary_action: Optional[str] = None
        self.primary_button = ttk.Button(actions, command=self.on_primary, width=14)
        self.primary_button.grid(row=0, column=0)
        self.more_button = ttk.Menubutton(actions, text="More")
        self.more_menu = tk.Menu(self.more_button, tearoff=False)
        self.more_menu.add_command(label="Reinstall service", command=self.on_install)
        self.more_menu.add_command(label="Uninstall service...", command=self.on_uninstall)
        self.more_menu.add_separator()
        self.more_menu.add_command(label="Open service log", command=self.on_open_log)
        self.more_menu.add_command(label="Open settings folder", command=self.on_open_folder)
        self.more_button["menu"] = self.more_menu
        self.more_button.grid(row=0, column=1, padx=(8, 0))
        return banner

    def _build_form(self, parent: ttk.Frame) -> ttk.Frame:
        form = ttk.Frame(parent)
        form.columnconfigure(1, weight=1)
        row = self._section(form, 0, "Printer", first=True)

        line = ttk.Frame(form)
        line.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        line.columnconfigure(1, weight=1)
        self.printer_dot = tk.Canvas(line, width=12, height=12, highlightthickness=0)
        self.printer_dot_shape = self.printer_dot.create_oval(1, 1, 11, 11, width=0)
        self.printer_dot.grid(row=0, column=0, padx=(0, 6))
        self.printer_text = tk.StringVar()
        ttk.Label(line, textvariable=self.printer_text).grid(row=0, column=1, sticky="w")
        self.zadig_button = ttk.Button(line, text="Open Zadig", command=self.on_open_zadig)
        self.zadig_button.grid(row=0, column=2, sticky="e")
        if not zadig.is_supported():
            self.zadig_button.state(["disabled"])
        row += 1

        ttk.Label(form, text="USB ID").grid(row=row, column=0, sticky="w", pady=3)
        ids = ttk.Frame(form)
        ids.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        self._entry(ids, "printerVendorId", width=9).grid(row=0, column=0)
        ttk.Label(ids, text="vendor").grid(row=0, column=1, padx=(4, 14))
        self._entry(ids, "printerProductId", width=9).grid(row=0, column=2)
        ttk.Label(ids, text="product").grid(row=0, column=3, padx=(4, 0))
        row += 1

        ttk.Label(form, text="Paper cutter").grid(row=row, column=0, sticky="w", pady=3)
        variable = tk.BooleanVar()
        cutter = ttk.Checkbutton(form, variable=variable)
        cutter.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        self._register("hasCutter", variable, cutter)
        row += 1

        ttk.Label(form, text="Copies per print").grid(row=row, column=0, sticky="w", pady=3)
        variable = tk.StringVar()
        copies = ttk.Spinbox(form, from_=1, to=config.MAX_COPIES, width=4, textvariable=variable)
        copies.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        self._register("copies", variable, copies)
        row += 1

        row = self._section(form, row, "Invoice")
        row = self._field(form, row, "School name", "schoolName")
        row = self._field(form, row, "Address", "schoolAddress")
        row = self._field(form, row, "Phone", "schoolPhone")
        row = self._field(form, row, "Email", "schoolEmail")
        row = self._field(form, row, "Footer", "invoiceFooter")

        row = self._section(form, row, "Connection")
        ttk.Label(form, text="Port").grid(row=row, column=0, sticky="w", pady=3)
        self._entry(form, "port", width=9).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        self._field(form, row + 1, "Frontend URL", "frontendUrl")
        return form

    def _section(self, form: ttk.Frame, row: int, title: str, first: bool = False) -> int:
        heading = ttk.Frame(form)
        heading.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0 if first else 14, 6))
        heading.columnconfigure(1, weight=1)
        ttk.Label(heading, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Separator(heading).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        return row + 1

    def _field(self, form: ttk.Frame, row: int, label: str, key: str) -> int:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
        self._entry(form, key, width=36).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        return row + 1

    def _entry(self, parent: tk.Widget, key: str, width: int) -> ttk.Entry:
        variable = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        self._register(key, variable, entry)
        return entry

    def _register(self, key: str, variable: tk.Variable, widget: tk.Widget) -> None:
        self.entries[key] = variable
        self.widgets[key] = widget
        variable.trace_add("write", lambda *unused: self._on_change())

    def _build_preview(self, parent: ttk.Frame) -> ttk.Frame:
        """The paper as it will print, updated while typing."""
        column = ttk.Frame(parent)
        ttk.Label(column, text="Preview", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        paper = tk.Frame(column, bg="#C9CED6", padx=1, pady=1)
        paper.grid(row=1, column=0, columnspan=2)
        self.preview = tk.Text(
            paper, width=printer.MAX_LINE_WIDTH, height=28, font=self.font_paper,
            bg=PAPER, fg="#111111", relief="flat", padx=12, pady=10, wrap="none",
            highlightthickness=0, cursor="arrow", state="disabled",
        )
        self.preview.grid(row=0, column=0)
        scroll = ttk.Scrollbar(paper, orient="vertical", command=self.preview.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=scroll.set)
        self.preview_note = tk.StringVar()
        ttk.Label(column, textvariable=self.preview_note, style="Hint.TLabel").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        self.test_button = ttk.Button(column, text="Print test ticket", command=self.on_test_print)
        self.test_button.grid(row=2, column=1, sticky="e", pady=(6, 0))
        column.columnconfigure(0, weight=1)
        return column

    def _build_footer(self, parent: tk.Widget) -> ttk.Frame:
        footer = ttk.Frame(parent, padding=(18, 10))
        footer.columnconfigure(0, weight=1)
        self.message = tk.StringVar()
        self.message_label = ttk.Label(footer, textvariable=self.message, wraplength=520, justify="left")
        self.message_label.grid(row=0, column=0, sticky="w")
        self.revert_button = ttk.Button(footer, text="Revert", command=self.on_revert)
        self.revert_button.grid(row=0, column=1, padx=(8, 0))
        self.save_button = ttk.Button(footer, text="Save", command=self.on_save, default="active")
        self.save_button.grid(row=0, column=2, padx=(8, 0))
        return footer

    # -- form state --------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self.busy_text is not None

    def show_settings(self, settings: Dict) -> None:
        self._loading = True
        for key, variable in self.entries.items():
            value = settings[key]
            variable.set(value if isinstance(value, bool) else str(value))
        self._loading = False
        self._on_change()

    def form_values(self) -> Dict[str, object]:
        return {key: variable.get() for key, variable in self.entries.items()}

    def is_dirty(self) -> bool:
        try:
            return config.validate(self.form_values()) != self.settings
        except config.ConfigError:
            return True

    def set_message(self, text: str, error: bool = False) -> None:
        self.message.set(text)
        self.message_label.configure(style="Error.TLabel" if error else "TLabel")

    def _on_change(self) -> None:
        if self._loading:
            return
        values = self.form_values()
        text = render_preview(values)
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")
        copies = preview_copies(values)
        plural = "s" if copies > 1 else ""
        self.preview_note.set(
            f"{copies} separate ticket{plural}" if values.get("hasCutter")
            else f"{copies} cop{'ies' if copies > 1 else 'y'} on one strip"
        )
        if self.is_dirty():
            self.set_message("Unsaved changes.")
        elif self.message.get() == "Unsaved changes.":
            self.set_message("")
        self.update_controls()

    def on_revert(self) -> None:
        self.show_settings(self.settings)
        self.set_message("")

    def on_save(self) -> None:
        if self.busy:
            return
        values = self.form_values()
        try:
            saved = config.save(values)
        except config.ConfigError as error:
            self.set_message(str(error), error=True)
            self._focus_offending_field(str(error))
            return
        needs_restart = any(saved[key] != self.settings[key] for key in RESTART_FIELDS)
        self.settings = saved
        self.show_settings(saved)
        if needs_restart and self.probe_result.status == service_manager.RUNNING:
            self.run_action("Restarting the service...", service_manager.restart,
                            done="Settings saved and service restarted.")
        else:
            self.set_message("Settings saved.")

    def _focus_offending_field(self, message: str) -> None:
        for key, label in config.LABELS.items():
            if message.startswith(label) and key in self.widgets:
                self.widgets[key].focus_set()
                return

    # -- service -----------------------------------------------------------

    def on_primary(self) -> None:
        action = self.primary_action
        if action == "install":
            self.on_install()
        elif action == "start":
            self.run_action("Starting the service...", service_manager.start, done="Service started.")
        elif action == "stop":
            self.run_action("Stopping the service...", service_manager.stop, done="Service stopped.")
        elif action == "restart":
            self.run_action("Restarting the service...", service_manager.restart, done="Service restarted.")

    def on_install(self) -> None:
        self.run_action("Installing the service...", service_manager.install,
                        done="Service installed and started.")

    def on_uninstall(self) -> None:
        if messagebox.askyesno(APP_NAME, "Stop and remove the service?", parent=self.root):
            self.run_action("Removing the service...", service_manager.uninstall, done="Service removed.")

    def on_open_log(self) -> None:
        self._open(os.path.join(config.app_dir(), "service.log"), "There is no service log yet.")

    def on_open_folder(self) -> None:
        self._open(config.app_dir(), "The settings folder is missing.")

    def _open(self, path: str, missing: str) -> None:
        if not os.path.exists(path):
            self.set_message(missing)
            return
        try:
            open_path(path)
        except OSError as error:
            self.set_message(f"Cannot open {path}: {error}", error=True)

    def on_open_zadig(self) -> None:
        try:
            path, bundled = zadig.open_zadig()
        except zadig.ZadigError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self.root)
            return
        origin = "bundled copy" if bundled else path
        self.set_message(f"Zadig opened ({origin}).")

    def on_test_print(self) -> None:
        if self.is_dirty():
            self.set_message("Save the settings first.", error=True)
            return
        self.run_action("Printing a test ticket...", lambda: printer.pos_print(TEST_INVOICE),
                        done="Test ticket sent to the printer.")

    def run_action(self, progress: str, action: Callable[[], None], done: str) -> None:
        """Run a slow operation off the UI thread, showing it in the banner."""
        if self.busy:
            return
        self.busy_text = progress
        self.set_message("")
        self.update_banner()
        self.update_controls()

        def work() -> None:
            try:
                action()
                self.results.put(("action", done, None))
            except Exception as error:  # shown to the user, never fatal
                self.results.put(("action", None, str(error) or type(error).__name__))

        threading.Thread(target=work, daemon=True).start()

    # -- live state --------------------------------------------------------

    def _quick_probe(self) -> Probe:
        """Service state only: fast enough to run before the window shows."""
        if not service_manager.is_supported():
            return Probe(None, None, None)
        try:
            return Probe(service_manager.status(), None, None)
        except service_manager.ServiceError as error:
            return Probe(None, None, None, str(error))

    def refresh(self) -> None:
        """Probe now, on this thread."""
        self.apply_probe(probe(self.settings))

    def apply_probe(self, result: Probe) -> None:
        self.probe_result = result
        self.update_banner()
        self.update_controls()

    def _start_probe(self) -> None:
        if self._probing:
            return
        self._probing = True
        settings = dict(self.settings)
        threading.Thread(
            target=lambda: self.results.put(("probe", probe(settings), None)), daemon=True
        ).start()

    def _tick(self) -> None:
        while True:
            try:
                kind, payload, error = self.results.get_nowait()
            except queue.Empty:
                break
            if kind == "probe":
                self._probing = False
                self.apply_probe(payload)
            else:
                self.busy_text = None
                self.set_message(payload or "")
                self._since_probe = PROBE_EVERY_MS
                self.update_banner()
                self.update_controls()
                if error:
                    messagebox.showerror(APP_NAME, error, parent=self.root)
        self._since_probe += TICK_MS
        if self._since_probe >= PROBE_EVERY_MS:
            self._since_probe = 0
            self._start_probe()
        self._after_id = self.root.after(TICK_MS, self._tick)

    def close(self) -> None:
        """Stop the background refresh."""
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.close()

    def current_view(self) -> ServiceView:
        if self.busy:
            return ServiceView("busy", self.busy_text or "", "", None)
        return describe_service(self.probe_result, self.settings["port"], service_manager.is_supported())

    def update_banner(self) -> None:
        view = self.current_view()
        background, accent = TONES[view.tone]
        for widget in (self.banner, self.dot, self.banner_title, self.banner_detail, self.banner_actions):
            widget.configure(bg=background)
        self.dot.itemconfigure(self.dot_shape, fill=accent)
        self.banner_title.configure(text=view.title)
        self.banner_detail.configure(text=view.detail)
        self.root.title(f"{APP_NAME} - {view.title}")

        if self.busy:
            self.progress.grid(row=1, column=1, sticky="w", pady=(4, 0))
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()

        self.primary_action = view.primary
        if view.primary:
            self.primary_button.configure(text=PRIMARY_LABELS[view.primary])
            self.primary_button.grid()
        else:
            self.primary_button.grid_remove()

        connected = self.probe_result.printer
        colour, text = {
            True: (TONES["ok"][1], "Printer detected"),
            False: (TONES["bad"][1], "Printer not detected. Driver missing?"),
            None: (TONES["idle"][1], "Printer status unknown"),
        }[connected]
        self.printer_dot.itemconfigure(self.printer_dot_shape, fill=colour)
        self.printer_text.set(text)

    def update_controls(self) -> None:
        status = self.probe_result.status
        installed = status in (service_manager.STOPPED, service_manager.RUNNING, service_manager.PENDING)
        idle = not self.busy

        def enable(widget: ttk.Widget, condition: bool) -> None:
            widget.state(["!disabled"] if condition else ["disabled"])

        enable(self.primary_button, idle)
        self.more_menu.entryconfigure(0, state="normal" if idle and installed else "disabled")
        self.more_menu.entryconfigure(1, state="normal" if idle and installed else "disabled")
        dirty = self.is_dirty()
        enable(self.save_button, idle and dirty)
        enable(self.revert_button, idle and dirty)
        enable(self.test_button, idle)


def run() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
