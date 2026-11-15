from pathlib import Path
from datetime import datetime, timedelta
from utils.path_validator import PathValidator
from utils.logger import AuditLogger


class SearchService:
    """
    Handles all search operations across the file system.
    Search by name, extension, date modified, and file size.
    """

    def __init__(self, validator: PathValidator, logger: AuditLogger) -> None:
        self._validator = validator
        self._logger = logger

    def by_name(self, folder: str, name: str) -> str:
        """Find files whose name contains the given string (case-insensitive)."""
        p = self._validator.validate(folder)
        results = [
            str(f) for f in p.rglob("*")
            if f.is_file() and name.lower() in f.name.lower()
        ]
        self._logger.log("search_by_name", folder, detail=f"query={name} found={len(results)}")
        if not results:
            return f"No files matching '{name}' found in {p.name}"
        return f"Found {len(results)} file(s) matching '{name}':\n" + "\n".join(results)

    def by_extension(self, folder: str, ext: str) -> str:
        """Find all files with a specific extension (e.g. .pdf, .py)."""
        ext = ext if ext.startswith(".") else f".{ext}"
        p = self._validator.validate(folder)
        results = [str(f) for f in p.rglob(f"*{ext}") if f.is_file()]
        self._logger.log("search_by_extension", folder, detail=f"ext={ext} found={len(results)}")
        if not results:
            return f"No '{ext}' files found in {p.name}"
        return f"Found {len(results)} '{ext}' file(s):\n" + "\n".join(results)

    def by_date(self, folder: str, days: int = 7) -> str:
        """Find files modified within the last N days."""
        p = self._validator.validate(folder)
        cutoff = datetime.now() - timedelta(days=days)
        results = []
        for f in p.rglob("*"):
            if f.is_file():
                modified = datetime.fromtimestamp(f.stat().st_mtime)
                if modified >= cutoff:
                    results.append((modified, str(f)))
        results.sort(key=lambda x: x[0], reverse=True)
        self._logger.log("search_by_date", folder, detail=f"days={days} found={len(results)}")
        if not results:
            return f"No files modified in the last {days} day(s) in {p.name}"
        lines = [f"Files modified in the last {days} day(s):"]
        lines.extend(
            f"  {mod.strftime('%Y-%m-%d %H:%M')}  {path}"
            for mod, path in results
        )
        return "\n".join(lines)

    def by_size(self, folder: str, min_mb: float = 0.0, max_mb: float = 9999.0) -> str:
        """Find files whose size is between min_mb and max_mb megabytes."""
        p = self._validator.validate(folder)
        min_bytes = min_mb * 1024 * 1024
        max_bytes = max_mb * 1024 * 1024
        results = []
        for f in p.rglob("*"):
            if f.is_file():
                size = f.stat().st_size
                if min_bytes <= size <= max_bytes:
                    results.append((size, str(f)))
        results.sort(reverse=True)
        self._logger.log("search_by_size", folder, detail=f"min={min_mb}MB max={max_mb}MB found={len(results)}")
        if not results:
            return f"No files between {min_mb}MB and {max_mb}MB found in {p.name}"
        lines = [f"Files between {min_mb}MB and {max_mb}MB:"]
        lines.extend(
            f"  {size / 1024**2:.2f} MB  {path}"
            for size, path in results
        )
        return "\n".join(lines)
