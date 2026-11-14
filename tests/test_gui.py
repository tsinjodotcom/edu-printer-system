import json
import os
import tempfile
import time
import unittest
from unittest import mock

import config
import service_manager as sm

try:
    import tkinter as tk
    import gui
except ImportError:  # Python built without Tk
    tk = None


@unittest.skipIf(tk is None, "tkinter is not available")
class GuiTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.status = sm.NOT_INSTALLED
        self.operations = []
        replacements = [
            (config, "app_dir", lambda: self.folder),
            (sm, "is_supported", lambda: True),
            (sm, "status", lambda: self.status),
        ]
        for name in ("install", "uninstall", "start", "stop", "restart"):
            replacements.append((sm, name, lambda name=name: self.operations.append(name)))
        for owner, name, replacement in replacements:
            patcher = mock.patch.object(owner, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.errors = self.patch_messagebox("showerror")

    def patch_messagebox(self, name, **kwargs):
        patcher = mock.patch.object(gui.messagebox, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def open_window(self):
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"no display: {error}")
        root.withdraw()
        self.addCleanup(root.destroy)
        return gui.App(root)

    def wait_until_idle(self, app):
        deadline = time.time() + 5
        while app.busy and time.time() < deadline:
            app.root.update()
            time.sleep(0.01)
        self.assertFalse(app.busy, "the operation never finished")

    def enabled(self, button):
        return not button.instate(["disabled"])

    def saved_file(self):
        with open(os.path.join(self.folder, "config.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def test_form_shows_defaults_when_no_config_exists(self):
        app = self.open_window()
        self.assertEqual(app.form_values()["port"], "5050")
        self.assertEqual(app.form_values()["schoolName"], config.DEFAULTS["schoolName"])
        self.assertIn("not created yet", app.config_file_text.get())

    def test_form_shows_values_from_the_config_file(self):
        config.save({"port": 6000, "invoiceFooter": "Merci."})
        app = self.open_window()
        self.assertEqual(app.form_values()["port"], "6000")
        self.assertEqual(app.form_values()["invoiceFooter"], "Merci.")
        self.assertNotIn("not created yet", app.config_file_text.get())

    def test_broken_config_file_is_reported_and_defaults_shown(self):
        with open(os.path.join(self.folder, "config.json"), "w") as handle:
            handle.write("{ broken")
        app = self.open_window()
        self.assertIn("default settings", app.message.get())
        self.assertEqual(app.form_values()["port"], "5050")

    def test_save_creates_the_config_file_from_the_form(self):
        app = self.open_window()
        app.entries["schoolName"].set("Ecole Test")
        app.entries["printerVendorId"].set("4b43")
        app.on_save()
        self.assertEqual(self.saved_file()["schoolName"], "Ecole Test")
        self.assertEqual(self.saved_file()["printerVendorId"], "0x4B43")
        self.assertEqual(app.form_values()["printerVendorId"], "0x4B43")
        self.assertEqual(app.message.get(), "Settings saved.")
        self.assertNotIn("not created yet", app.config_file_text.get())

    def test_invalid_value_is_refused_with_a_message(self):
        app = self.open_window()
        app.entries["port"].set("abc")
        app.on_save()
        self.assertIn("Port", self.errors.call_args.args[1])
        self.assertFalse(os.path.exists(os.path.join(self.folder, "config.json")))

    def test_saving_a_new_port_restarts_a_running_service(self):
        self.status = sm.RUNNING
        app = self.open_window()
        app.entries["port"].set("6001")
        app.on_save()
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["restart"])
        self.assertEqual(app.message.get(), "Settings saved and service restarted.")

    def test_saving_print_settings_does_not_restart(self):
        self.status = sm.RUNNING
        app = self.open_window()
        app.entries["invoiceFooter"].set("Merci.")
        app.on_save()
        self.assertEqual(self.operations, [])

    def test_buttons_follow_the_service_status(self):
        app = self.open_window()
        buttons = (app.install_button, app.uninstall_button, app.start_button, app.stop_button)
        expected = {
            sm.NOT_INSTALLED: ("Install service", [True, False, False, False]),
            sm.STOPPED: ("Reinstall service", [True, True, True, False]),
            sm.RUNNING: ("Reinstall service", [True, True, False, True]),
        }
        for status, (label, states) in expected.items():
            with self.subTest(status=status):
                self.status = status
                app.refresh_status()
                self.assertEqual(app.install_button.cget("text"), label)
                self.assertEqual([self.enabled(button) for button in buttons], states)
                self.assertEqual(app.status_text.get(), gui.STATUS_TEXT[status])

    def test_install_button_installs_and_reports(self):
        app = self.open_window()
        app.on_install()
        self.assertFalse(self.enabled(app.install_button))
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["install"])
        self.assertEqual(app.message.get(), "Service installed and started.")

    def test_uninstall_asks_first(self):
        self.status = sm.RUNNING
        ask = self.patch_messagebox("askyesno", return_value=False)
        app = self.open_window()
        app.on_uninstall()
        self.assertEqual(self.operations, [])
        ask.return_value = True
        app.on_uninstall()
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["uninstall"])

    def test_failed_operation_shows_the_error(self):
        app = self.open_window()
        with mock.patch.object(sm, "install", side_effect=sm.ServiceError("Access is denied.")):
            app.on_install()
            self.wait_until_idle(app)
        self.assertEqual(self.errors.call_args.args[1], "Access is denied.")
        self.assertTrue(self.enabled(app.install_button))

    def test_service_controls_are_disabled_off_windows(self):
        with mock.patch.object(sm, "is_supported", lambda: False):
            app = self.open_window()
            self.assertEqual(app.status_text.get(), "Available on Windows only")
            self.assertFalse(self.enabled(app.install_button))
            self.assertTrue(self.enabled(app.save_button))


if __name__ == "__main__":
    unittest.main()
