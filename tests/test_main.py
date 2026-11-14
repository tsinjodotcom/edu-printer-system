import unittest
from unittest import mock

import config
import main
import service_manager


class AppTest(unittest.TestCase):
    def setUp(self):
        self.client = main.create_app(dict(config.DEFAULTS, frontendUrl="http://front.test")).test_client()

    def test_health(self):
        with mock.patch.object(main, "usb_backend_name", return_value="usb.backend.libusb1"):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "healthy", "usbBackend": "usb.backend.libusb1"})

    def test_print_passes_the_invoice_to_the_printer(self):
        with mock.patch.object(main, "pos_print") as pos_print:
            response = self.client.post("/print", json={"invoiceNumber": "F-1"})
        self.assertEqual(response.status_code, 204)
        pos_print.assert_called_once_with({"invoiceNumber": "F-1"})

    def test_cors_allows_only_the_configured_frontend(self):
        allowed = self.client.get("/", headers={"Origin": "http://front.test"})
        other = self.client.get("/", headers={"Origin": "http://elsewhere.test"})
        self.assertEqual(allowed.headers.get("Access-Control-Allow-Origin"), "http://front.test")
        self.assertIsNone(other.headers.get("Access-Control-Allow-Origin"))


class CommandLineTest(unittest.TestCase):
    def test_no_argument_opens_the_window(self):
        fake_gui = mock.Mock()
        with mock.patch.dict("sys.modules", {"gui": fake_gui}):
            self.assertEqual(main.main([]), 0)
        fake_gui.run.assert_called_once_with()

    def test_serve_runs_the_server(self):
        with mock.patch.object(main, "serve") as serve:
            self.assertEqual(main.main(["serve"]), 0)
        serve.assert_called_once_with()

    def test_install_and_uninstall(self):
        for command in ("install", "uninstall"):
            with self.subTest(command=command), mock.patch.object(service_manager, command) as operation:
                self.assertEqual(main.main([command]), 0)
                operation.assert_called_once_with()

    def test_service_failure_gives_exit_code_1(self):
        failure = service_manager.ServiceError("denied")
        with mock.patch.object(service_manager, "install", side_effect=failure), \
                mock.patch("sys.stderr"):
            self.assertEqual(main.main(["install"]), 1)

    def test_unknown_command_gives_exit_code_2(self):
        with mock.patch("sys.stderr"):
            self.assertEqual(main.main(["nonsense"]), 2)

    def test_serve_uses_the_configured_port(self):
        app = mock.Mock()
        with mock.patch.object(main, "setup_logging"), \
                mock.patch.object(config, "load", return_value=dict(config.DEFAULTS, port=6010)), \
                mock.patch.object(main, "create_app", return_value=app):
            main.serve()
        self.assertEqual(app.run.call_args.kwargs["port"], 6010)


if __name__ == "__main__":
    unittest.main()
