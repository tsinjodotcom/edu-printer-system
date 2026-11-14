import hashlib
import os
import tempfile
import unittest
from unittest import mock

import zadig


class ZadigTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.app_folder = os.path.join(folder.name, "app")
        self.temp_folder = os.path.join(folder.name, "temp")
        os.makedirs(self.app_folder)
        os.makedirs(self.temp_folder)
        self.bundled = os.path.join(folder.name, "bundle", "zadig.exe")
        os.makedirs(os.path.dirname(self.bundled))
        self.write(self.bundled, b"bundled zadig")
        self.on_path = None
        self.started = []
        replacements = [
            (zadig, "app_dir", lambda: self.app_folder),
            (zadig, "bundled_path", lambda: self.bundled),
            (zadig, "is_supported", lambda: True),
            (zadig.shutil, "which", lambda name: self.on_path),
            (zadig.tempfile, "gettempdir", lambda: self.temp_folder),
        ]
        for owner, name, replacement in replacements:
            patcher = mock.patch.object(owner, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(zadig.os, "startfile", self.started.append, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, path, content):
        with open(path, "wb") as handle:
            handle.write(content)

    def test_bundled_copy_is_used_when_the_pc_has_no_zadig(self):
        path, bundled = zadig.open_zadig()
        self.assertTrue(bundled)
        self.assertEqual(self.started, [path])
        self.assertEqual(path, os.path.join(self.temp_folder, "EduPrinterSystem", "zadig-2.9.exe"))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"bundled zadig")

    def test_bundled_copy_is_extracted_outside_the_bundle(self):
        path, _ = zadig.locate()
        self.assertNotEqual(os.path.dirname(path), os.path.dirname(self.bundled))

    def test_extracted_copy_is_reused(self):
        first, _ = zadig.locate()
        stamp = os.path.getmtime(first)
        os.utime(first, (stamp - 100, stamp - 100))
        second, _ = zadig.locate()
        self.assertEqual(first, second)
        self.assertEqual(os.path.getmtime(second), stamp - 100)

    def test_damaged_extracted_copy_is_replaced(self):
        path, _ = zadig.locate()
        self.write(path, b"cut")
        zadig.locate()
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"bundled zadig")

    def test_zadig_next_to_the_exe_is_preferred(self):
        beside = os.path.join(self.app_folder, "zadig-2.8.exe")
        self.write(beside, b"theirs")
        self.assertEqual(zadig.open_zadig(), (beside, False))
        self.assertEqual(self.started, [beside])
        self.assertEqual(os.listdir(self.temp_folder), [])

    def test_zadig_on_the_path_is_preferred(self):
        self.on_path = os.path.join(self.app_folder, "elsewhere", "zadig.exe")
        self.assertEqual(zadig.open_zadig(), (self.on_path, False))
        self.assertEqual(self.started, [self.on_path])

    def test_missing_bundle_is_reported(self):
        os.remove(self.bundled)
        with self.assertRaises(zadig.ZadigError):
            zadig.open_zadig()
        self.assertEqual(self.started, [])

    def test_failure_to_start_is_reported(self):
        with mock.patch.object(zadig.os, "startfile", side_effect=OSError("cancelled"), create=True):
            with self.assertRaises(zadig.ZadigError) as caught:
                zadig.open_zadig()
        self.assertIn("cancelled", str(caught.exception))

    def test_refuses_to_run_off_windows(self):
        with mock.patch.object(zadig, "is_supported", lambda: False):
            with self.assertRaises(zadig.ZadigError):
                zadig.open_zadig()
        self.assertEqual(self.started, [])


class VendoredZadigTest(unittest.TestCase):
    """The binary shipped in the repo is the official, unmodified release."""

    SHA256 = "4ecaa95df3da3621486a043aef8b3050b8bafe7c901402871e816229ef82039b"

    def test_vendored_binary_matches_the_official_release(self):
        path = zadig.bundled_path()
        self.assertEqual(path, os.path.join(zadig.app_dir(), "vendor", "zadig", "zadig.exe"))
        with open(path, "rb") as handle:
            content = handle.read()
        self.assertEqual(content[:2], b"MZ")
        self.assertEqual(hashlib.sha256(content).hexdigest(), self.SHA256)


if __name__ == "__main__":
    unittest.main()
