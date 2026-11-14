import os
import sys
import tempfile
import types
import unittest
from unittest import mock

import service_manager as sm


class FakeWindows:
    """Stands in for Windows: a service registry plus a recording NSSM."""

    def __init__(self, state=sm.NOT_INSTALLED):
        self.state = state
        self.calls = []

    def status(self):
        return self.state

    def nssm(self, *args, check=True):
        self.calls.append(args)
        verb = args[0]
        if verb == "install":
            self.state = sm.STOPPED
        elif verb in ("start", "restart"):
            self.state = sm.RUNNING
        elif verb == "stop":
            self.state = sm.STOPPED
        elif verb == "remove":
            self.state = sm.NOT_INSTALLED
        return 0

    def verbs(self):
        return [args[0] for args in self.calls]


class ServiceOperationsTest(unittest.TestCase):
    def use(self, windows):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        for target, replacement in (
            ("is_supported", lambda: True),
            ("status", windows.status),
            ("_nssm", windows.nssm),
            ("app_dir", lambda: self.folder),
        ):
            patcher = mock.patch.object(sm, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        return windows

    def test_install_registers_configures_and_starts(self):
        windows = self.use(FakeWindows())
        with mock.patch.object(sm, "serve_command", return_value=["C:\\app\\Edu.exe", "serve"]):
            sm.install()
        self.assertEqual(windows.calls[0], ("install", sm.SERVICE_NAME, "C:\\app\\Edu.exe", "serve"))
        self.assertIn(("set", sm.SERVICE_NAME, "Start", "SERVICE_AUTO_START"), windows.calls)
        self.assertIn(("set", sm.SERVICE_NAME, "AppDirectory", self.folder), windows.calls)
        self.assertEqual(windows.calls[-1], ("start", sm.SERVICE_NAME))
        self.assertEqual(windows.state, sm.RUNNING)

    def test_install_replaces_an_existing_service(self):
        windows = self.use(FakeWindows(sm.RUNNING))
        sm.install()
        self.assertEqual(windows.verbs()[:3], ["stop", "remove", "install"])
        self.assertEqual(windows.state, sm.RUNNING)

    def test_uninstall_stops_then_removes(self):
        windows = self.use(FakeWindows(sm.RUNNING))
        sm.uninstall()
        self.assertEqual(windows.calls, [("stop", sm.SERVICE_NAME), ("remove", sm.SERVICE_NAME, "confirm")])
        self.assertEqual(windows.state, sm.NOT_INSTALLED)

    def test_uninstall_deletes_the_nssm_copy(self):
        self.use(FakeWindows(sm.STOPPED))
        copy = sm.installed_nssm_path()
        open(copy, "w").close()
        sm.uninstall()
        self.assertFalse(os.path.exists(copy))

    def test_uninstall_when_not_installed_does_nothing(self):
        windows = self.use(FakeWindows())
        sm.uninstall()
        self.assertEqual(windows.calls, [])

    def test_stop_is_skipped_when_already_stopped(self):
        windows = self.use(FakeWindows(sm.STOPPED))
        sm.stop()
        self.assertEqual(windows.calls, [])

    def test_start_stop_restart(self):
        windows = self.use(FakeWindows(sm.STOPPED))
        sm.start()
        sm.restart()
        sm.stop()
        self.assertEqual(windows.verbs(), ["start", "restart", "stop"])


class NssmProcessTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.bundled = os.path.join(self.folder, "bundled-nssm.exe")
        with open(self.bundled, "wb") as handle:
            handle.write(b"nssm")
        for target, replacement in (
            ("app_dir", lambda: self.folder),
            ("bundled_nssm_path", lambda: self.bundled),
        ):
            patcher = mock.patch.object(sm, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_nssm(self, returncode=0, stdout=b"", **kwargs):
        completed = types.SimpleNamespace(returncode=returncode, stdout=stdout)
        with mock.patch.object(sm.subprocess, "run", return_value=completed) as run:
            result = sm._nssm("start", sm.SERVICE_NAME, **kwargs)
        return result, run

    def test_nssm_is_copied_next_to_the_exe_and_run_from_there(self):
        _, run = self.run_nssm()
        copy = os.path.join(self.folder, "nssm.exe")
        with open(copy, "rb") as handle:
            self.assertEqual(handle.read(), b"nssm")
        self.assertEqual(run.call_args.args[0], [copy, "start", sm.SERVICE_NAME])

    def test_failure_raises_with_nssm_utf16_output(self):
        with self.assertRaises(sm.ServiceError) as caught:
            self.run_nssm(returncode=1, stdout="Access is denied.".encode("utf-16-le"))
        self.assertIn("Access is denied.", str(caught.exception))

    def test_failure_can_be_tolerated(self):
        result, _ = self.run_nssm(returncode=3, check=False)
        self.assertEqual(result, 3)

    def test_missing_bundled_nssm_is_reported(self):
        os.remove(self.bundled)
        with self.assertRaises(sm.ServiceError):
            self.run_nssm()


class EnvironmentTest(unittest.TestCase):
    def test_built_exe_serves_itself(self):
        with mock.patch.object(sm, "is_frozen", return_value=True), \
                mock.patch.object(sys, "executable", os.path.abspath("EduPrinterSystem.exe")):
            self.assertEqual(sm.serve_command(), [os.path.abspath("EduPrinterSystem.exe"), "serve"])

    def test_source_run_serves_through_main_py(self):
        command = sm.serve_command()
        self.assertEqual(command[1:], [os.path.join(os.path.dirname(sm.__file__), "main.py"), "serve"])

    @unittest.skipIf(sys.platform == "win32", "checks the non-Windows guard")
    def test_operations_refuse_to_run_off_windows(self):
        for operation in (sm.status, sm.install, sm.uninstall, sm.start, sm.stop, sm.restart):
            with self.subTest(operation=operation.__name__), self.assertRaises(sm.ServiceError):
                operation()

    @unittest.skipUnless(sys.platform == "win32", "queries the real service manager")
    def test_status_of_an_unknown_service_on_windows(self):
        with mock.patch.object(sm, "SERVICE_NAME", "EduPrinterServiceDoesNotExist"):
            self.assertEqual(sm.status(), sm.NOT_INSTALLED)


if __name__ == "__main__":
    unittest.main()
