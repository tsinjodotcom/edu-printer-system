import unittest
from datetime import datetime
from unittest import mock

import config
import printer
from printer import (
    MAX_LINE_WIDTH,
    format_currency,
    format_label_value,
    generate_invoice_string,
    pos_print,
)
from escpos.exceptions import USBNotFoundError

PRINTED_AT = datetime(2026, 11, 14, 21, 30)
LONG_NAME = "RAKOTONDRAZAKA Andriamihaja Tsiory Fanomezantsoa"


def make_invoice(**overrides):
    invoice = {
        "invoiceNumber": "F-2026-0412",
        "clientName": "RAKOTO Jean",
        "paidDate": "2026-11-14T10:30:00",
        "payments": [{"methodPaymentId": 1, "amount": 190000}],
        "elements": [
            {"description": "Ecolage novembre", "amount": 150000},
            {"description": "Cantine", "amount": 40000},
        ],
    }
    invoice.update(overrides)
    return invoice


def settings_with(**overrides):
    return {**config.DEFAULTS, **overrides}


def render(settings=None, **overrides):
    """Invoice lines, rendered with the default settings plus `settings`."""
    invoice = make_invoice(**overrides)
    return generate_invoice_string(invoice, settings_with(**(settings or {})), PRINTED_AT).split("\n")


class FormatCurrencyTest(unittest.TestCase):
    def test_below_one_million_is_printed_in_full(self):
        self.assertEqual(format_currency(0), "0")
        self.assertEqual(format_currency(500), "500")
        self.assertEqual(format_currency(150000), "150 000")
        self.assertEqual(format_currency(999999), "999 999")

    def test_decimals_are_dropped_not_rounded(self):
        self.assertEqual(format_currency(1500.99), "1 500")
        self.assertEqual(format_currency(999999.9), "999 999")

    def test_one_million_and_above_uses_m(self):
        self.assertEqual(format_currency(1000000), "1M")
        self.assertEqual(format_currency(1500000), "1,5M")
        self.assertEqual(format_currency(1250000), "1,25M")
        self.assertEqual(format_currency(12000000), "12M")

    def test_m_abbreviation_keeps_every_digit(self):
        self.assertEqual(format_currency(1234567), "1,234567M")
        self.assertEqual(format_currency(2000050), "2,00005M")
        self.assertEqual(format_currency(1000001), "1,000001M")

    def test_thousands_of_millions_are_grouped(self):
        self.assertEqual(format_currency(1500000000), "1 500M")

    def test_negative_amounts(self):
        self.assertEqual(format_currency(-40000), "-40 000")
        self.assertEqual(format_currency(-2500000), "-2,5M")


class FormatLabelValueTest(unittest.TestCase):
    def test_labels_are_padded_to_the_same_width(self):
        self.assertEqual(format_label_value("FACTURE", "F-1"), "FACTURE.: F-1")
        self.assertEqual(format_label_value("CLIENT", "Jean"), "CLIENT..: Jean")
        self.assertEqual(format_label_value("PAYEE LE", "x"), "PAYEE LE: x")

    def test_long_value_wraps_without_trailing_newline(self):
        result = format_label_value("CLIENT", LONG_NAME)
        self.assertGreater(len(result.split("\n")), 1)
        self.assertFalse(result.endswith("\n"))


class InvoiceLayoutTest(unittest.TestCase):
    def test_payee_le_follows_client_directly(self):
        lines = render()
        client = lines.index("CLIENT..: RAKOTO Jean")
        self.assertEqual(lines[client + 1], "PAYEE LE: 14/11/2026 10:30")

    def test_payee_le_follows_wrapped_client_directly(self):
        lines = render(clientName=LONG_NAME)
        payee = lines.index("PAYEE LE: 14/11/2026 10:30")
        self.assertEqual(lines[payee - 1], "Fanomezantsoa")

    def test_invoice_has_no_blank_lines(self):
        for name in ("RAKOTO Jean", LONG_NAME):
            with self.subTest(name=name):
                self.assertNotIn("", [line.strip() for line in render(clientName=name)])

    def test_payment_method_follows_payee_le(self):
        lines = render()
        payee = lines.index("PAYEE LE: 14/11/2026 10:30")
        self.assertEqual(lines[payee + 1], "PAYE PAR: Especes")
        self.assertEqual(lines[payee + 2], "-" * MAX_LINE_WIDTH)

    def test_each_payment_method_is_named(self):
        expected = {1: "Especes", 2: "MVola", 3: "Airtel Money", 4: "Orange Money", 9: "Methode 9"}
        for method_id, name in expected.items():
            with self.subTest(method_id=method_id):
                lines = render(payments=[{"methodPaymentId": method_id}])
                self.assertIn(f"PAYE PAR: {name}", lines)

    def test_several_payments_list_each_method_once(self):
        payments = [{"methodPaymentId": 2}, {"methodPaymentId": 1}, {"methodPaymentId": 2}]
        self.assertIn("PAYE PAR: MVola, Especes", render(payments=payments))

    def test_many_methods_wrap_within_the_paper_width(self):
        payments = [{"methodPaymentId": i} for i in (1, 2, 3, 4)]
        lines = render(payments=payments)
        start = lines.index("PAYE PAR: Especes, MVola, Airtel")
        self.assertEqual(lines[start + 1], "Money, Orange Money")
        self.assertTrue(all(len(line) <= MAX_LINE_WIDTH for line in lines))

    def test_payment_line_is_present_even_without_payment(self):
        for payments in ([], None):
            with self.subTest(payments=payments):
                self.assertIn("PAYE PAR: --", render(payments=payments))
        invoice = make_invoice()
        del invoice["payments"]
        self.assertIn("PAYE PAR: --", generate_invoice_string(invoice, settings_with()).split("\n"))
        unpaid = render(paidDate=None, payments=[])
        self.assertEqual(unpaid[unpaid.index("CLIENT..: RAKOTO Jean") + 1], "PAYE PAR: --")

    def test_print_date_sits_between_total_and_footer(self):
        lines = render()
        self.assertEqual(lines[-3:], [
            "-" * MAX_LINE_WIDTH,
            "Imprime le: 14/11/2026 21:30",
            "Merci pour votre confiance.",
        ])

    def test_print_date_defaults_to_now(self):
        now = datetime(2027, 1, 2, 8, 5)
        with mock.patch.object(printer, "datetime") as clock:
            clock.now.return_value = now
            text = generate_invoice_string(make_invoice(), settings_with())
        self.assertIn("\nImprime le: 02/01/2027 08:05\n", text)

    def test_payee_le_is_omitted_without_paid_date(self):
        lines = render(paidDate=None)
        self.assertFalse(any(line.startswith("PAYEE LE") for line in lines))

    def test_lines_fit_the_paper_width(self):
        elements = [
            {"description": "Frais d'inscription et fournitures scolaires", "amount": 1234500},
            {"description": "Cantine", "amount": 40000},
        ]
        for line in render(clientName=LONG_NAME, elements=elements):
            self.assertLessEqual(len(line), MAX_LINE_WIDTH, line)

    def test_amount_is_never_shortened_by_a_long_description(self):
        elements = [{"description": "Frais d'inscription et fournitures scolaires", "amount": 987654}]
        lines = render(elements=elements)
        first = next(line for line in lines if line.startswith("Frais"))
        self.assertTrue(first.endswith(" 987 654"))
        self.assertEqual(len(first), MAX_LINE_WIDTH)

    def test_total_sums_elements_and_uses_m(self):
        elements = [
            {"description": "Ecolage annuel", "amount": 1500000},
            {"description": "Cantine", "amount": 40000},
        ]
        lines = render(elements=elements)
        total = next(line for line in lines if line.startswith("TOTAL"))
        self.assertTrue(total.endswith(" 1,54M"))
        self.assertEqual(len(total), MAX_LINE_WIDTH)


class InvoiceSettingsTest(unittest.TestCase):
    def test_default_header_and_footer(self):
        lines = render()
        self.assertEqual(lines[0], "ECOLE EXEMPLE")
        self.assertEqual(lines[1], "+261 00 00 000 00")
        self.assertEqual(lines[-1], "Merci pour votre confiance.")

    def test_header_comes_from_settings(self):
        lines = render({"schoolName": "Ecole Test", "schoolPhone": "034 00 000 00"})
        self.assertEqual(lines[0], "ECOLE TEST")
        self.assertEqual(lines[1], "034 00 000 00")

    def test_footer_comes_from_settings(self):
        lines = render({"invoiceFooter": "Merci et a bientot."})
        self.assertEqual(lines[-1], "Merci et a bientot.")
        self.assertNotIn("Merci pour votre confiance.", lines)

    def test_empty_footer_prints_no_footer_line(self):
        lines = render({"invoiceFooter": ""})
        self.assertEqual(lines[-1], "Imprime le: 14/11/2026 21:30")


class PosPrintTest(unittest.TestCase):
    def run_print(self, device, settings=None):
        with mock.patch.object(config, "load", return_value=settings_with(**(settings or {}))), \
                mock.patch.object(printer, "open_printer", return_value=device) as opener:
            pos_print(make_invoice())
        return opener

    def printed(self, settings):
        """What the printer received, in order: texts, and "CUT" for cuts."""
        device = mock.Mock()
        self.run_print(device, settings)
        return ["CUT" if call[0] == "cut" else call.args[0]
                for call in device.method_calls if call[0] in ("text", "cut")]

    def test_prints_two_copies_by_default_with_one_cut(self):
        device = mock.Mock()
        self.run_print(device)
        invoice = generate_invoice_string(make_invoice(), settings_with())
        printed = [call.args[0] for call in device.text.call_args_list]
        self.assertEqual(printed, [invoice, "\n" + "=" * MAX_LINE_WIDTH + "\n", invoice])
        device.cut.assert_called_once_with()

    def test_copies_setting_without_cutter(self):
        invoice = generate_invoice_string(make_invoice(), settings_with())
        separator = "\n" + "=" * MAX_LINE_WIDTH + "\n"
        self.assertEqual(self.printed({"copies": 1}), [invoice, "CUT"])
        self.assertEqual(
            self.printed({"copies": 3}),
            [invoice, separator, invoice, separator, invoice, "CUT"],
        )

    def test_cutter_cuts_after_each_copy_without_separator(self):
        invoice = generate_invoice_string(make_invoice(), settings_with())
        self.assertEqual(
            self.printed({"hasCutter": True, "copies": 2}),
            [invoice, "CUT", invoice, "CUT"],
        )
        self.assertEqual(self.printed({"hasCutter": True, "copies": 1}), [invoice, "CUT"])
        self.assertEqual(
            self.printed({"hasCutter": True, "copies": 3}),
            [invoice, "CUT", invoice, "CUT", invoice, "CUT"],
        )

    def test_usb_is_released_after_printing(self):
        device = mock.Mock()
        self.run_print(device)
        device.close.assert_called_once_with()

    def test_usb_is_released_when_printing_fails(self):
        device = mock.Mock()
        device.text.side_effect = RuntimeError("paper out")
        with self.assertRaises(RuntimeError):
            self.run_print(device)
        device.close.assert_called_once_with()

    def test_printer_ids_come_from_settings(self):
        opener = self.run_print(
            mock.Mock(), {"printerVendorId": "0x1234", "printerProductId": "0xABCD"}
        )
        opener.assert_called_once_with(0x1234, 0xABCD)

    def test_footer_setting_reaches_the_paper(self):
        device = mock.Mock()
        self.run_print(device, {"invoiceFooter": "Merci.", "copies": 1})
        self.assertTrue(device.text.call_args.args[0].endswith("\nMerci."))


class PrinterConnectedTest(unittest.TestCase):
    def check(self, bundled, results):
        import usb.core
        with mock.patch.object(printer, "get_usb_backend", return_value=bundled), \
                mock.patch.object(usb.core, "find", side_effect=results) as find:
            return printer.printer_connected(0x1234, 0xABCD), find

    def test_found_through_the_bundled_libusb(self):
        connected, find = self.check("bundled", ["device"])
        self.assertIs(connected, True)
        find.assert_called_once_with(idVendor=0x1234, idProduct=0xABCD, backend="bundled")

    def test_found_through_the_system_libusb_only(self):
        connected, find = self.check("bundled", [None, "device"])
        self.assertIs(connected, True)
        self.assertEqual(find.call_args_list[1], mock.call(idVendor=0x1234, idProduct=0xABCD))

    def test_not_plugged_in(self):
        self.assertIs(self.check("bundled", [None, None])[0], False)

    def test_unknown_when_no_libusb_can_be_loaded(self):
        import usb.core
        failure = usb.core.NoBackendError("No backend available")
        self.assertIsNone(self.check(None, [failure, failure])[0])


class OpenPrinterTest(unittest.TestCase):
    def test_bundled_backend_is_tried_first(self):
        with mock.patch.object(printer, "get_usb_backend", return_value="bundled"), \
                mock.patch.object(printer, "Usb", return_value="device") as usb:
            self.assertEqual(printer.open_printer(1, 2), "device")
        usb.assert_called_once_with(1, 2, usb_args={"backend": "bundled"})

    def test_falls_back_to_system_libusb_when_device_not_found(self):
        with mock.patch.object(printer, "get_usb_backend", return_value="bundled"), \
                mock.patch.object(printer, "Usb", side_effect=[USBNotFoundError(), "device"]) as usb:
            self.assertEqual(printer.open_printer(1, 2), "device")
        self.assertEqual(usb.call_args_list[1], mock.call(1, 2))

    def test_uses_system_libusb_when_nothing_is_bundled(self):
        with mock.patch.object(printer, "get_usb_backend", return_value=None), \
                mock.patch.object(printer, "Usb", return_value="device") as usb:
            self.assertEqual(printer.open_printer(1, 2), "device")
        usb.assert_called_once_with(1, 2)


if __name__ == "__main__":
    unittest.main()
