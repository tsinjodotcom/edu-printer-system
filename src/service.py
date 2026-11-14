import win32serviceutil
import win32service
import servicemanager
import socket
import sys
import os
from main import app

class FlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = "EduPrinterService"
    _svc_display_name_ = "Edu Printer System Service"
    _svc_description_ = "Invoice printing service for education system"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32serviceutil.win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True

    def SvcStop(self):
        self.ReportServiceStatus(win32serviceutil.win32service.SERVICE_STOP_PENDING)
        win32serviceutil.win32event.SetEvent(self.stop_event)
        self.is_alive = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        port = int(os.getenv("PORT", "5050"))
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FlaskService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FlaskService)

