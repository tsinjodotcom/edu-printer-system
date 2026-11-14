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
    gui = None

# One Tk instance for the whole module, as in the real app: creating a
# second one in the same process makes Tk's event loop hang on macOS.
_root = None


def shared_root():
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    return _root


def tearDownModule():
    global _root
    if _root is not None:
        _root.destroy()
        _root = None


@unittest.skipIf(gui is None, "tkinter is not available")
class DescribeServiceTest(unittest.TestCase):
    """What the banner says for each state of the PC."""

    def view(self, status, healthy=None, error=None, supported=True):
        return gui.describe_service(gui.Probe(status, healthy, None, error), 5050, supported)

    def test_not_installed_offers_install(self):
        view = self.view(sm.NOT_INSTALLED)
        self.assertEqual((view.tone, view.title, view.primary), ("idle", "Service not installed", "install"))

    def test_stopped_warns_and_offers_start(self):
        view = self.view(sm.STOPPED)
        self.assertEqual((view.tone, view.title, view.primary), ("warn", "Service stopped", "start"))

    def test_running_and_answering_is_green(self):
        view = self.view(sm.RUNNING, healthy=True)
        self.assertEqual((view.tone, view.title, view.primary), ("ok", "Service running", "stop"))
        self.assertEqual(view.detail, "http://localhost:5050")

    def test_running_before_the_first_health_check(self):
        view = self.view(sm.RUNNING, healthy=None)
        self.assertEqual((view.tone, view.title), ("ok", "Service running"))

    def test_running_but_not_answering_is_flagged(self):
        view = self.view(sm.RUNNING, healthy=False)
        self.assertEqual((view.tone, view.primary), ("bad", "restart"))
        self.assertIn("not answering", view.title)
        self.assertIn("service log", view.detail)

    def test_transition_has_no_action(self):
        view = self.view(sm.PENDING)
        self.assertEqual((view.tone, view.primary), ("busy", None))

    def test_unreadable_state_shows_the_error(self):
        view = self.view(None, error="Access is denied.")
        self.assertEqual((view.tone, view.detail, view.primary), ("bad", "Access is denied.", None))

    def test_off_windows(self):
        view = self.view(None, supported=False)
        self.assertEqual((view.tone, view.primary), ("idle", None))


@unittest.skipIf(gui is None, "tkinter is not available")
class ProbeTest(unittest.TestCase):
    def run_probe(self, status, healthy=True, connected=True):
        settings = dict(config.DEFAULTS, port=6000, printerVendorId="0x1234", printerProductId="0xABCD")
        with mock.patch.object(sm, "is_supported", lambda: True), \
                mock.patch.object(sm, "status", lambda: status), \
                mock.patch.object(gui, "check_health", return_value=healthy) as health, \
                mock.patch.object(gui.printer, "printer_connected", return_value=connected) as usb:
            return gui.probe(settings), health, usb

    def test_running_service_is_health_checked_on_its_port(self):
        result, health, usb = self.run_probe(sm.RUNNING, healthy=False)
        self.assertEqual(result, gui.Probe(sm.RUNNING, False, True))
        health.assert_called_once_with(6000)
        usb.assert_called_once_with(0x1234, 0xABCD)

    def test_stopped_service_is_not_health_checked(self):
        result, health, _ = self.run_probe(sm.STOPPED)
        self.assertIsNone(result.healthy)
        health.assert_not_called()

    def test_service_error_is_carried(self):
        with mock.patch.object(sm, "is_supported", lambda: True), \
                mock.patch.object(sm, "status", side_effect=sm.ServiceError("denied")), \
                mock.patch.object(gui.printer, "printer_connected", return_value=None):
            result = gui.probe(dict(config.DEFAULTS))
        self.assertEqual((result.status, result.error), (None, "denied"))

    def test_nothing_is_probed_off_windows(self):
        with mock.patch.object(sm, "is_supported", lambda: False):
            self.assertEqual(gui.probe(dict(config.DEFAULTS)), gui.Probe(None, None, None))

    def test_health_check_fails_quietly_when_nothing_listens(self):
        self.assertFalse(gui.check_health(1))


@unittest.skipIf(gui is None, "tkinter is not available")
class PreviewTest(unittest.TestCase):
    def values(self, **overrides):
        return {**config.DEFAULTS, **overrides}

    def test_one_strip_with_separator_and_final_cut(self):
        text = gui.render_preview(self.values(copies="2"))
        self.assertEqual(text.count("=" * 32), 1)
        self.assertEqual(text.count(gui.CUT_MARK), 1)
        self.assertTrue(text.endswith(gui.CUT_MARK))
        self.assertEqual(text.count("FACTURE.:"), 2)

    def test_cutter_shows_a_cut_after_each_copy(self):
        text = gui.render_preview(self.values(copies="3", hasCutter=True))
        self.assertEqual(text.count(gui.CUT_MARK), 3)
        self.assertNotIn("=" * 32, text)

    def test_unsaved_header_and_footer_are_shown(self):
        text = gui.render_preview(self.values(schoolName="Ecole Test", invoiceFooter="A bientot."))
        self.assertTrue(text.startswith("ECOLE TEST\n"))
        self.assertIn("\nA bientot.\n", text)

    def test_invalid_copies_still_render(self):
        for bad in ("", "abc", "0", "99"):
            with self.subTest(copies=bad):
                self.assertIn("FACTURE.:", gui.render_preview(self.values(copies=bad)))
        self.assertEqual(gui.preview_copies({"copies": "99"}), config.MAX_COPIES)

    def test_lines_fit_the_paper(self):
        text = gui.render_preview(self.values(hasCutter=True))
        self.assertTrue(all(len(line) <= 32 for line in text.split("\n")))


@unittest.skipIf(gui is None, "tkinter is not available")
class WindowTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.status = sm.NOT_INSTALLED
        self.healthy = True
        self.connected = True
        self.operations = []
        replacements = [
            (config, "app_dir", lambda: self.folder),
            (sm, "is_supported", lambda: True),
            (sm, "status", lambda: self.status),
            (gui, "check_health", lambda port: self.healthy),
            (gui.printer, "printer_connected", lambda vendor, product: self.connected),
            (gui.zadig, "is_supported", lambda: True),
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

    def open_window(self, refresh=True):
        """A fresh window; any window opened earlier in the test is closed."""
        try:
            root = shared_root()
        except tk.TclError as error:
            self.skipTest(f"no display: {error}")
        self.close_window()
        self.app = gui.App(root)
        self.addCleanup(self.close_window)
        if refresh:
            self.app.refresh()
        return self.app

    def close_window(self):
        app = getattr(self, "app", None)
        if app is not None:
            app.close()
            for child in app.root.winfo_children():
                child.destroy()
            self.app = None

    def wait_until_idle(self, app):
        deadline = time.time() + 5
        while app.busy and time.time() < deadline:
            app.root.update()
            time.sleep(0.01)
        self.assertFalse(app.busy, "the operation never finished")

    def enabled(self, widget):
        return not widget.instate(["disabled"])

    def menu_enabled(self, app, index):
        return app.more_menu.entrycget(index, "state") == "normal"

    def saved_file(self):
        with open(os.path.join(self.folder, "config.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def preview_text(self, app):
        return app.preview.get("1.0", "end-1c")

    # -- service state -----------------------------------------------------

    def test_banner_and_title_show_the_service_state(self):
        app = self.open_window()
        expected = {
            sm.NOT_INSTALLED: ("Service not installed", "Install service", "idle"),
            sm.STOPPED: ("Service stopped", "Start", "warn"),
            sm.RUNNING: ("Service running", "Stop", "ok"),
        }
        for status, (title, button, tone) in expected.items():
            with self.subTest(status=status):
                self.status = status
                app.refresh()
                self.assertEqual(app.banner_title.cget("text"), title)
                self.assertEqual(app.root.title(), f"Edu Printer System - {title}")
                self.assertEqual(app.primary_button.cget("text"), button)
                self.assertEqual(app.banner.cget("bg"), gui.TONES[tone][0])
                self.assertTrue(self.enabled(app.primary_button))

    def test_state_is_known_as_soon_as_the_window_opens(self):
        self.status = sm.RUNNING
        app = self.open_window(refresh=False)
        self.assertEqual(app.banner_title.cget("text"), "Service running")

    def test_running_but_not_answering_is_visible(self):
        self.status = sm.RUNNING
        self.healthy = False
        app = self.open_window()
        self.assertEqual(app.banner_title.cget("text"), "Service running, but not answering")
        self.assertEqual(app.banner.cget("bg"), gui.TONES["bad"][0])
        self.assertEqual(app.primary_button.cget("text"), "Restart")
        app.primary_button.invoke()
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["restart"])

    def test_state_changes_outside_the_window_are_picked_up(self):
        app = self.open_window()
        self.status = sm.RUNNING
        deadline = time.time() + 6
        while app.banner_title.cget("text") != "Service running" and time.time() < deadline:
            app.root.update()
            time.sleep(0.02)
        self.assertEqual(app.banner_title.cget("text"), "Service running")

    def test_reinstall_and_uninstall_need_an_installed_service(self):
        app = self.open_window()
        self.assertEqual([self.menu_enabled(app, 0), self.menu_enabled(app, 1)], [False, False])
        self.status = sm.STOPPED
        app.refresh()
        self.assertEqual([self.menu_enabled(app, 0), self.menu_enabled(app, 1)], [True, True])

    def test_primary_button_installs_and_shows_progress(self):
        app = self.open_window()
        app.primary_button.invoke()
        self.assertEqual(app.banner_title.cget("text"), "Installing the service...")
        self.assertEqual(app.banner.cget("bg"), gui.TONES["busy"][0])
        self.assertFalse(self.enabled(app.primary_button))
        self.assertFalse(self.enabled(app.save_button))
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["install"])
        self.assertEqual(app.message.get(), "Service installed and started.")

    def test_start_and_stop(self):
        self.status = sm.STOPPED
        app = self.open_window()
        app.primary_button.invoke()
        self.wait_until_idle(app)
        self.status = sm.RUNNING
        app.refresh()
        app.primary_button.invoke()
        self.wait_until_idle(app)
        self.assertEqual(self.operations, ["start", "stop"])

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
        self.assertTrue(self.enabled(app.primary_button))

    def test_off_windows_the_service_is_unavailable_but_settings_work(self):
        with mock.patch.object(sm, "is_supported", lambda: False), \
                mock.patch.object(gui.zadig, "is_supported", lambda: False):
            app = self.open_window()
            self.assertEqual(app.banner_title.cget("text"), "Service unavailable")
            self.assertFalse(app.primary_button.winfo_ismapped())
            self.assertFalse(self.enabled(app.zadig_button))
            app.entries["schoolName"].set("Ecole Test")
            self.assertTrue(self.enabled(app.save_button))

    # -- printer -----------------------------------------------------------

    def test_printer_detection_is_shown(self):
        app = self.open_window()
        for connected, text in ((True, "Printer detected"), (False, "Printer not detected. Driver missing?"),
                                (None, "Printer status unknown")):
            with self.subTest(connected=connected):
                self.connected = connected
                app.refresh()
                self.assertEqual(app.printer_text.get(), text)

    def test_open_zadig_button_reports_which_copy_was_opened(self):
        app = self.open_window()
        with mock.patch.object(gui.zadig, "open_zadig", return_value=("C:\\tmp\\zadig-2.9.exe", True)):
            app.zadig_button.invoke()
        self.assertEqual(app.message.get(), "Zadig opened (bundled copy).")
        with mock.patch.object(gui.zadig, "open_zadig", return_value=("C:\\tools\\zadig.exe", False)):
            app.zadig_button.invoke()
        self.assertEqual(app.message.get(), "Zadig opened (C:\\tools\\zadig.exe).")

    def test_open_zadig_failure_is_shown(self):
        app = self.open_window()
        with mock.patch.object(gui.zadig, "open_zadig", side_effect=gui.zadig.ZadigError("Cannot start")):
            app.on_open_zadig()
        self.assertEqual(self.errors.call_args.args[1], "Cannot start")

    def test_test_ticket_prints_with_the_saved_settings(self):
        app = self.open_window()
        with mock.patch.object(gui.printer, "pos_print") as pos_print:
            app.test_button.invoke()
            self.wait_until_idle(app)
        pos_print.assert_called_once_with(gui.TEST_INVOICE)
        self.assertEqual(app.message.get(), "Test ticket sent to the printer.")

    def test_test_ticket_needs_saved_settings(self):
        app = self.open_window()
        app.entries["copies"].set("1")
        with mock.patch.object(gui.printer, "pos_print") as pos_print:
            app.test_button.invoke()
        pos_print.assert_not_called()
        self.assertIn("Save the settings first", app.message.get())

    def test_test_ticket_failure_is_shown(self):
        app = self.open_window()
        with mock.patch.object(gui.printer, "pos_print", side_effect=RuntimeError("USB device not found")):
            app.on_test_print()
            self.wait_until_idle(app)
        self.assertEqual(self.errors.call_args.args[1], "USB device not found")

    # -- settings ----------------------------------------------------------

    def test_form_shows_defaults_when_no_config_exists(self):
        app = self.open_window()
        self.assertEqual(app.form_values()["port"], "5050")
        self.assertEqual(app.form_values()["schoolName"], config.DEFAULTS["schoolName"])
        self.assertEqual(set(app.form_values()), set(config.DEFAULTS))
        self.assertFalse(self.enabled(app.save_button))

    def test_form_shows_values_from_the_config_file(self):
        config.save({"port": 6000, "invoiceFooter": "Merci."})
        app = self.open_window()
        self.assertEqual(app.form_values()["port"], "6000")
        self.assertEqual(app.form_values()["invoiceFooter"], "Merci.")

    def test_broken_config_file_is_reported_and_defaults_shown(self):
        with open(os.path.join(self.folder, "config.json"), "w") as handle:
            handle.write("{ broken")
        app = self.open_window()
        self.assertIn("default settings", app.message.get())
        self.assertEqual(app.form_values()["port"], "5050")

    def test_editing_marks_unsaved_changes_and_revert_restores(self):
        app = self.open_window()
        app.entries["schoolName"].set("Ecole Test")
        self.assertEqual(app.message.get(), "Unsaved changes.")
        self.assertTrue(self.enabled(app.save_button))
        self.assertTrue(self.enabled(app.revert_button))
        app.revert_button.invoke()
        self.assertEqual(app.form_values()["schoolName"], config.DEFAULTS["schoolName"])
        self.assertEqual(app.message.get(), "")
        self.assertFalse(self.enabled(app.save_button))

    def test_typing_the_same_value_back_clears_unsaved_changes(self):
        app = self.open_window()
        app.entries["copies"].set("3")
        app.entries["copies"].set("2")
        self.assertEqual(app.message.get(), "")
        self.assertFalse(self.enabled(app.save_button))

    def test_preview_follows_the_form(self):
        app = self.open_window()
        self.assertTrue(self.preview_text(app).startswith("ECOLE EXEMPLE\n"))
        self.assertEqual(app.preview_note.get(), "2 copies on one strip")
        app.entries["schoolName"].set("Ecole Test")
        app.entries["hasCutter"].set(True)
        app.entries["copies"].set("1")
        self.assertTrue(self.preview_text(app).startswith("ECOLE TEST\n"))
        self.assertEqual(self.preview_text(app).count(gui.CUT_MARK), 1)
        self.assertEqual(app.preview_note.get(), "1 separate ticket")

    def test_address_and_email_are_editable_previewed_and_saved(self):
        app = self.open_window()
        self.assertEqual((app.form_values()["schoolAddress"], app.form_values()["schoolEmail"]), ("", ""))
        app.entries["schoolAddress"].set("Lot 12, Antananarivo")
        app.entries["schoolEmail"].set("contact@ecole.test")
        preview = self.preview_text(app).split("\n")
        self.assertEqual(preview[1], "Lot 12, Antananarivo")
        self.assertEqual(preview[3], "contact@ecole.test")
        app.save_button.invoke()
        self.assertEqual(self.saved_file()["schoolAddress"], "Lot 12, Antananarivo")
        self.assertEqual(self.saved_file()["schoolEmail"], "contact@ecole.test")

    def test_save_creates_the_config_file_from_the_form(self):
        app = self.open_window()
        app.entries["schoolName"].set("Ecole Test")
        app.entries["printerVendorId"].set("4b43")
        app.save_button.invoke()
        self.assertEqual(self.saved_file()["schoolName"], "Ecole Test")
        self.assertEqual(self.saved_file()["printerVendorId"], "0x4B43")
        self.assertEqual(app.form_values()["printerVendorId"], "0x4B43")
        self.assertEqual(app.message.get(), "Settings saved.")
        self.assertFalse(self.enabled(app.save_button))

    def test_cutter_and_copies_are_shown_and_saved(self):
        app = self.open_window()
        self.assertIs(app.form_values()["hasCutter"], False)
        self.assertEqual(app.form_values()["copies"], "2")
        app.entries["hasCutter"].set(True)
        app.entries["copies"].set("1")
        app.on_save()
        self.assertIs(self.saved_file()["hasCutter"], True)
        self.assertEqual(self.saved_file()["copies"], 1)
        self.assertEqual(self.operations, [])

        reopened = self.open_window()
        self.assertIs(reopened.form_values()["hasCutter"], True)
        self.assertEqual(reopened.form_values()["copies"], "1")

    def test_invalid_value_is_refused_in_place(self):
        for key, bad, label in (("port", "abc", "Port"), ("copies", "9", "Copies per print"),
                                ("printerVendorId", "zz", "Printer vendor ID")):
            with self.subTest(field=key):
                app = self.open_window()
                app.entries[key].set(bad)
                app.on_save()
                self.assertIn(label, app.message.get())
                self.assertEqual(str(app.message_label.cget("style")), "Error.TLabel")
                self.assertFalse(os.path.exists(os.path.join(self.folder, "config.json")))
                self.errors.assert_not_called()

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

    def test_open_log_without_a_log_says_so(self):
        app = self.open_window()
        with mock.patch.object(gui, "open_path") as open_path:
            app.on_open_log()
            self.assertEqual(app.message.get(), "There is no service log yet.")
            open(os.path.join(self.folder, "service.log"), "w").close()
            app.on_open_log()
            app.on_open_folder()
        self.assertEqual([call.args[0] for call in open_path.call_args_list],
                         [os.path.join(self.folder, "service.log"), self.folder])


if __name__ == "__main__":
    unittest.main()
