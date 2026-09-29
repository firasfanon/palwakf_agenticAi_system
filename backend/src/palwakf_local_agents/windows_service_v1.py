from __future__ import annotations

import os

from palwakf_local_agents.outbound_worker_v1 import OutboundWorkerV1, load_worker_config

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:  # pragma: no cover - Windows-only dependency
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = None


if win32serviceutil is not None:
    class PalWakfOutboundExecutorService(win32serviceutil.ServiceFramework):
        _svc_name_ = "PalWakfOutboundLocalExecutorV1"
        _svc_display_name_ = "PalWakf Outbound Local Executor V1"
        _svc_description_ = "Governed outbound-only PalWakf local execution provider."

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.worker: OutboundWorkerV1 | None = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self.worker is not None:
                self.worker.stop()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogInfoMsg("PalWakfOutboundLocalExecutorV1 starting")
            config_path = os.environ.get("PALWAKF_EXECUTOR_CONFIG")
            if not config_path:
                servicemanager.LogErrorMsg("PALWAKF_EXECUTOR_CONFIG_NOT_SET")
                raise RuntimeError("PALWAKF_EXECUTOR_CONFIG_NOT_SET")
            self.worker = OutboundWorkerV1(load_worker_config(config_path))
            self.worker.run()
else:
    PalWakfOutboundExecutorService = None


def main() -> None:
    if win32serviceutil is None or PalWakfOutboundExecutorService is None:
        raise RuntimeError("PYWIN32_REQUIRED_FOR_WINDOWS_SERVICE")
    win32serviceutil.HandleCommandLine(PalWakfOutboundExecutorService)


if __name__ == "__main__":
    main()
