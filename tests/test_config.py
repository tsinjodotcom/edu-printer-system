import json
import os
import tempfile
import unittest
from unittest import mock

import config


class ConfigFileTest(unittest.TestCase):
    """Runs against a temporary folder standing in for the exe's folder."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        patcher = mock.patch.object(config, "app_dir", return_value=self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name, text):
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def read_config(self):
        with open(config.config_path(), encoding="utf-8") as handle:
            return json.load(handle)

    def test_config_file_sits_in_the_app_folder(self):
        self.assertEqual(config.config_path(), os.path.join(self.folder, "config.json"))

    def test_missing_file_gives_defaults_and_is_not_created(self):
        self.assertEqual(config.load(), config.DEFAULTS)
        self.assertFalse(os.path.exists(config.config_path()))

    def test_values_are_read_from_the_file(self):
        self.write("config.json", json.dumps({"port": 6000, "invoiceFooter": "Merci."}))
        settings = config.load()
        self.assertEqual(settings["port"], 6000)
        self.assertEqual(settings["invoiceFooter"], "Merci.")

    def test_keys_missing_from_the_file_use_defaults(self):
        self.write("config.json", json.dumps({"port": 6000}))
        self.assertEqual(config.load()["schoolName"], config.DEFAULTS["schoolName"])

    def test_unknown_keys_are_ignored(self):
        self.write("config.json", json.dumps({"somethingElse": 1}))
        self.assertEqual(config.load(), config.DEFAULTS)

    def test_broken_json_is_reported_not_replaced_by_defaults(self):
        self.write("config.json", "{ not json")
        with self.assertRaises(config.ConfigError):
            config.load()

    def test_non_object_json_is_reported(self):
        self.write("config.json", "[1, 2]")
        with self.assertRaises(config.ConfigError):
            config.load()

    def test_save_creates_the_file(self):
        self.assertFalse(os.path.exists(config.config_path()))
        config.save({"schoolName": "Ecole Test"})
        on_disk = self.read_config()
        self.assertEqual(on_disk["schoolName"], "Ecole Test")
        self.assertEqual(set(on_disk), set(config.DEFAULTS))

    def test_save_then_load_round_trips(self):
        saved = config.save({"port": "6001", "printerVendorId": "4b43", "invoiceFooter": ""})
        self.assertEqual(config.load(), saved)
        self.assertEqual(saved["port"], 6001)
        self.assertEqual(saved["printerVendorId"], "0x4B43")
        self.assertEqual(saved["invoiceFooter"], "")

    def test_cutter_and_copies_round_trip_as_json_types(self):
        config.save({"hasCutter": True, "copies": "1"})
        on_disk = self.read_config()
        self.assertIs(on_disk["hasCutter"], True)
        self.assertEqual(on_disk["copies"], 1)
        self.assertEqual(config.load()["hasCutter"], True)

    def test_config_written_before_these_settings_keeps_todays_printing(self):
        self.write("config.json", json.dumps({"port": 5050, "schoolName": "Ecole"}))
        settings = config.load()
        self.assertEqual((settings["hasCutter"], settings["copies"]), (False, 2))

    def test_save_overwrites_an_existing_file(self):
        config.save({"schoolName": "Premier"})
        config.save({"schoolName": "Second"})
        self.assertEqual(self.read_config()["schoolName"], "Second")

    def test_save_keeps_accented_text_readable(self):
        config.save({"schoolName": "École Sainte-Thérèse"})
        with open(config.config_path(), encoding="utf-8") as handle:
            self.assertIn("École Sainte-Thérèse", handle.read())

    def test_rejected_settings_leave_the_file_untouched(self):
        config.save({"port": 6000})
        with self.assertRaises(config.ConfigError):
            config.save({"port": "abc"})
        self.assertEqual(self.read_config()["port"], 6000)
        self.assertEqual(os.listdir(self.folder), ["config.json"])

    def test_old_env_file_is_used_until_config_exists(self):
        self.write(".env", 'PORT=6002\nPRINTER_VENDOR_ID=0x1234\nSCHOOL_NAME="Ecole Env"\nSCHOOL_EMAIL=x@y.z\n')
        settings = config.load()
        self.assertEqual(settings["port"], 6002)
        self.assertEqual(settings["printerVendorId"], "0x1234")
        self.assertEqual(settings["schoolName"], "Ecole Env")
        self.assertEqual(settings["frontendUrl"], config.DEFAULTS["frontendUrl"])

    def test_old_env_address_and_email_are_carried_over(self):
        self.write(".env", 'SCHOOL_ADDRESS="Lot 12, Antananarivo"\nSCHOOL_EMAIL=contact@ecole.test\n')
        settings = config.load()
        self.assertEqual(settings["schoolAddress"], "Lot 12, Antananarivo")
        self.assertEqual(settings["schoolEmail"], "contact@ecole.test")

    def test_address_and_email_default_to_empty(self):
        self.assertEqual((config.DEFAULTS["schoolAddress"], config.DEFAULTS["schoolEmail"]), ("", ""))
        saved = config.save({"schoolAddress": "  Lot 12  ", "schoolEmail": " a@b.c "})
        self.assertEqual((saved["schoolAddress"], saved["schoolEmail"]), ("Lot 12", "a@b.c"))

    def test_config_file_wins_over_old_env_file(self):
        self.write(".env", "PORT=6002\n")
        self.write("config.json", json.dumps({"port": 6003}))
        self.assertEqual(config.load()["port"], 6003)


class ValidateTest(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(config.validate({}), config.DEFAULTS)

    def test_port_must_be_a_number_in_range(self):
        for bad in ("", "abc", "0", "70000", "-1", "50.5"):
            with self.subTest(port=bad), self.assertRaises(config.ConfigError) as caught:
                config.validate({"port": bad})
            self.assertIn("Port", str(caught.exception))

    def test_port_accepts_text_from_the_form(self):
        self.assertEqual(config.validate({"port": " 8080 "})["port"], 8080)

    def test_usb_ids_are_normalised(self):
        settings = config.validate({"printerVendorId": "28e9", "printerProductId": " 0x289 "})
        self.assertEqual(settings["printerVendorId"], "0x28E9")
        self.assertEqual(settings["printerProductId"], "0x0289")

    def test_usb_ids_must_be_hexadecimal_and_16_bit(self):
        for bad in ("", "printer", "0x1FFFF", "-1"):
            with self.subTest(usb_id=bad), self.assertRaises(config.ConfigError):
                config.validate({"printerVendorId": bad})

    def test_default_is_two_copies_on_one_strip(self):
        self.assertEqual(config.DEFAULTS["copies"], 2)
        self.assertIs(config.DEFAULTS["hasCutter"], False)

    def test_copies_must_be_between_1_and_5(self):
        self.assertEqual(config.validate({"copies": " 3 "})["copies"], 3)
        for bad in ("", "0", "6", "two", "1.5", "-1"):
            with self.subTest(copies=bad), self.assertRaises(config.ConfigError) as caught:
                config.validate({"copies": bad})
            self.assertIn("Copies", str(caught.exception))

    def test_has_cutter_must_be_a_boolean(self):
        self.assertIs(config.validate({"hasCutter": True})["hasCutter"], True)
        for bad in ("true", 1, None):
            with self.subTest(value=bad), self.assertRaises(config.ConfigError):
                config.validate({"hasCutter": bad})

    def test_frontend_url_is_required(self):
        with self.assertRaises(config.ConfigError):
            config.validate({"frontendUrl": "   "})

    def test_text_is_trimmed_and_footer_may_be_empty(self):
        settings = config.validate({"schoolName": "  Ecole  ", "invoiceFooter": ""})
        self.assertEqual(settings["schoolName"], "Ecole")
        self.assertEqual(settings["invoiceFooter"], "")

    def test_parse_usb_id(self):
        self.assertEqual(config.parse_usb_id("0x28E9"), 0x28E9)
        self.assertEqual(config.parse_usb_id("0289"), 0x0289)


if __name__ == "__main__":
    unittest.main()
