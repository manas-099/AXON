import logging
from pathlib import Path
from config.settings import Settings


class AuditLogger:
    """
    Singleton audit logger that records every AXON file operation.
    Every create, read, write, delete is written to audit.log.
    Uses the Singleton pattern — only one logger exists per process.
    """

    _instance: "AuditLogger | None" = None

    def __init__(self, log_file: Path) -> None:
        self._log_file = log_file
        self._logger = logging.getLogger("AXON.audit")
        if not self._logger.handlers:
            handler = logging.FileHandler(str(log_file), encoding="utf-8")
            handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    @classmethod
    def get_instance(cls, settings: Settings) -> "AuditLogger":
        """Factory method: return the singleton AuditLogger instance."""
        if cls._instance is None:
            cls._instance = cls(settings.log_file)
        return cls._instance

    def log(
        self,
        operation: str,
        path: str,
        status: str = "SUCCESS",
        detail: str = "",
    ) -> None:
        """Write a single audit log entry."""
        msg = f"{operation:<22} | {path}"
        if detail:
            msg += f" | {detail}"
        if status == "SUCCESS":
            self._logger.info(msg)
        else:
            self._logger.error(f"{msg} | STATUS={status}")

    def get_recent(self, lines: int = 50) -> str:
        """Return the last N lines from the audit log file."""
        if not self._log_file.exists():
            return "Audit log is empty."
        with open(self._log_file, encoding="utf-8") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:]
        return "".join(recent) if recent else "Audit log is empty."
