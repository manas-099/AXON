# AXON — Complete Setup Prompt (Full Code)

> Paste this entire prompt into any AI coding assistant.
> It will scaffold the full project, write every file with complete production-ready code.

---

## What You Are Building

**AXON** (Autonomous eXtensible OS Navigator) is a local MCP server that gives
any LLM full control over a Windows file system.
Architecture: **Clean Architecture** with OOP, Factory Methods, and Single Responsibility.

**We are building the MCP Server only. No LLM agent yet.**

---

## Coding Rules — Follow These For Every File

- Use **OOP** — every service and tool layer is a class
- Use **Factory Methods** — `from_env()`, `get_instance()`, `create_all()`, `create()`
- Use **Single Responsibility** — each class does one thing
- Use **Dependency Injection** — pass dependencies through constructors
- Use **type hints** everywhere
- Use **docstrings** on every class and method
- Never put business logic in the tools layer
- Never put MCP imports in the services layer

---

## Step 1 — Initialize Project

Run these commands:

```bash
uv init axon
cd axon
uv add fastmcp==4.1.4 send2trash==2.1.0 python-dotenv==1.0.1
```

---

## Step 2 — Create Exact Folder Structure

Create every folder and empty `__init__.py` file first:

```
axon/
│
├── tools/
│   ├── __init__.py
│   ├── file_ops.py
│   ├── folder_ops.py
│   ├── search_ops.py
│   ├── file_info.py
│   └── safety_ops.py
│
├── services/
│   ├── __init__.py
│   ├── file_service.py
│   ├── folder_service.py
│   ├── search_service.py
│   └── safety_service.py
│
├── utils/
│   ├── __init__.py
│   ├── path_validator.py
│   ├── logger.py
│   ├── recycle.py
│   └── undo.py
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── logs/
│   └── audit.log       ← create empty file
│
├── backups/
│   └── undo/           ← create this subfolder too
│
├── tests/
│   ├── __init__.py
│   ├── test_file_ops.py
│   ├── test_folder_ops.py
│   └── test_search_ops.py
│
├── main.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Step 3 — Write requirements.txt

```
fastmcp==4.1.4
send2trash==2.1.0
python-dotenv==1.0.1
```

---

## Step 4 — Write .env

```env
# AXON — Allowed Paths Configuration
# Only these folders can be accessed by AXON
# Use forward slashes even on Windows

ALLOWED_PATHS=C:/Users/YourUsername/Desktop,C:/Users/YourUsername/Documents,C:/Users/YourUsername/Downloads

BACKUP_DIR=./backups
LOG_FILE=./logs/audit.log
UNDO_STACK_FILE=./logs/undo_stack.json
```

---

## Step 5 — Write .gitignore

```
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
env/
.python-version
.env
logs/
backups/
.vscode/
.idea/
*.swp
*.egg-info/
dist/
```

---

## Step 6 — Write All Code Files

Write each file below with the **exact code shown**. Do not change structure.

---

### config/settings.py

```python
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """
    Immutable application settings loaded from environment variables.
    Use the factory method `from_env()` to create an instance.
    """

    allowed_paths: tuple[Path, ...]
    backup_dir: Path
    log_file: Path
    undo_stack_file: Path

    @classmethod
    def from_env(cls) -> "Settings":
        """Factory method: build Settings from .env file."""
        raw = os.getenv("ALLOWED_PATHS", "")
        allowed = tuple(
            Path(p.strip()) for p in raw.split(",") if p.strip()
        )
        backup_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
        log_file = Path(os.getenv("LOG_FILE", "./logs/audit.log"))
        undo_stack_file = Path(os.getenv("UNDO_STACK_FILE", "./logs/undo_stack.json"))

        # Ensure required directories exist at startup
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "undo").mkdir(parents=True, exist_ok=True)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            allowed_paths=allowed,
            backup_dir=backup_dir,
            log_file=log_file,
            undo_stack_file=undo_stack_file,
        )


# Module-level singleton
_instance: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance. Creates it on first call."""
    global _instance
    if _instance is None:
        _instance = Settings.from_env()
    return _instance
```

---

### utils/undo.py

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UndoEntry:
    """
    Represents a single reversible file system operation.
    Stored in the undo stack so the last action can be reversed.
    """

    operation: str
    path: str
    original_path: str = ""
    backup_path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON persistence."""
        return {
            "operation": self.operation,
            "path": self.path,
            "original_path": self.original_path,
            "backup_path": self.backup_path,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UndoEntry":
        """Deserialize from dictionary."""
        entry = cls(
            operation=data["operation"],
            path=data["path"],
            original_path=data.get("original_path", ""),
            backup_path=data.get("backup_path", ""),
        )
        entry.timestamp = data.get("timestamp", "")
        return entry
```

---

### utils/path_validator.py

```python
from pathlib import Path
from config.settings import Settings


class PathValidator:
    """
    Validates that all file/folder paths are inside the allowed directories.
    Acts as the security layer for every file operation.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: Application settings containing allowed paths.
        """
        self._allowed = settings.allowed_paths

    def is_allowed(self, path: str | Path) -> bool:
        """Return True if path is inside any configured allowed directory."""
        target = Path(path).resolve()
        for allowed in self._allowed:
            try:
                target.relative_to(allowed.resolve())
                return True
            except ValueError:
                continue
        return False

    def validate(self, path: str | Path) -> Path:
        """
        Validate path and return resolved Path object.

        Raises:
            ValueError: If path is outside all allowed directories.
        """
        resolved = Path(path).resolve()
        if not self.is_allowed(resolved):
            allowed_str = [str(p) for p in self._allowed]
            raise ValueError(
                f"Access denied: '{resolved}' is outside allowed directories.\n"
                f"Allowed: {allowed_str}"
            )
        return resolved

    def validate_pair(self, src: str | Path, dest: str | Path) -> tuple[Path, Path]:
        """Validate two paths at once and return both as resolved Paths."""
        return self.validate(src), self.validate(dest)
```

---

### utils/logger.py

```python
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
```

---

### utils/recycle.py

```python
from pathlib import Path
from send2trash import send2trash


class RecycleBin:
    """
    Wrapper around send2trash.
    Sends files and folders to the OS Recycle Bin instead of hard-deleting.
    """

    def send(self, path: str | Path) -> None:
        """
        Send a file or folder to the system Recycle Bin.

        Args:
            path: Path to the file or folder to delete safely.
        """
        send2trash(str(path))
```

---

### services/safety_service.py

```python
import json
import shutil
from datetime import datetime
from pathlib import Path
from config.settings import Settings
from utils.path_validator import PathValidator
from utils.logger import AuditLogger
from utils.recycle import RecycleBin
from utils.undo import UndoEntry


class SafetyService:
    """
    Manages safety operations: backup, undo, confirm-delete, and audit log.
    Maintains a persistent undo stack stored in logs/undo_stack.json.
    """

    def __init__(
        self,
        settings: Settings,
        validator: PathValidator,
        logger: AuditLogger,
        recycle: RecycleBin,
    ) -> None:
        self._settings = settings
        self._validator = validator
        self._logger = logger
        self._recycle = recycle
        self._undo_stack: list[UndoEntry] = []
        self._load_stack()

    # ── Undo Stack ────────────────────────────────────────────────────────

    def _load_stack(self) -> None:
        """Load undo stack from JSON file on startup."""
        f = self._settings.undo_stack_file
        if f.exists():
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                self._undo_stack = [UndoEntry.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self._undo_stack = []

    def _save_stack(self) -> None:
        """Persist undo stack to JSON file. Keeps last 20 entries."""
        f = self._settings.undo_stack_file
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(
                [e.to_dict() for e in self._undo_stack[-20:]],
                fh,
                indent=2,
            )

    def push_undo(self, entry: UndoEntry) -> None:
        """Push an undoable operation onto the stack and save."""
        self._undo_stack.append(entry)
        self._save_stack()

    def create_undo_backup(self, path: Path) -> Path:
        """
        Save a backup copy of a file to backups/undo/ before destructive ops.
        Returns the path to the backup file.
        """
        undo_dir = self._settings.backup_dir / "undo"
        undo_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = undo_dir / f"{path.stem}_{ts}{path.suffix}"
        shutil.copy2(path, backup)
        return backup

    # ── Public Tools ──────────────────────────────────────────────────────

    def backup_file(self, path: str) -> str:
        """Create a user-initiated backup copy in the backups/ directory."""
        src = self._validator.validate(path)
        if not src.is_file():
            raise FileNotFoundError(f"File not found: {src}")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self._settings.backup_dir / f"{src.stem}_{ts}{src.suffix}"
        shutil.copy2(src, dest)
        self._logger.log("backup_file", str(src), detail=f"saved to {dest}")
        return f"Backup created at: {dest}"

    def confirm_delete(self, path: str) -> str:
        """
        Return detailed file information before deletion.
        Call this before delete_file or delete_folder.
        """
        p = self._validator.validate(path)
        if not p.exists():
            return f"Path does not exist: {p}"
        stat = p.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        kind = "File" if p.is_file() else "Folder"
        return (
            f"⚠️  CONFIRM DELETE\n"
            f"Type     : {kind}\n"
            f"Name     : {p.name}\n"
            f"Path     : {p}\n"
            f"Size     : {size_kb:.1f} KB\n"
            f"Modified : {modified}\n\n"
            f"To confirm, call delete_file('{path}') or delete_folder('{path}')"
        )

    def undo_last(self) -> str:
        """Reverse the most recent undoable operation."""
        if not self._undo_stack:
            return "Nothing to undo — undo stack is empty."
        entry = self._undo_stack.pop()
        self._save_stack()
        result = self._reverse(entry)
        self._logger.log("undo_last", entry.path, detail=f"reversed {entry.operation}")
        return result

    def _reverse(self, entry: UndoEntry) -> str:
        """Internal: reverse a single UndoEntry based on operation type."""
        op = entry.operation
        try:
            if op == "create_file":
                Path(entry.path).unlink(missing_ok=True)
                return f"Undone: deleted '{entry.path}'"

            elif op == "copy_file":
                Path(entry.path).unlink(missing_ok=True)
                return f"Undone: deleted copy '{entry.path}'"

            elif op == "move_file":
                shutil.move(entry.path, entry.original_path)
                return f"Undone: moved '{entry.path}' back to '{entry.original_path}'"

            elif op == "rename_file":
                Path(entry.path).rename(entry.original_path)
                return f"Undone: renamed back to '{Path(entry.original_path).name}'"

            elif op in ("delete_file", "write_file", "append_file"):
                if entry.backup_path and Path(entry.backup_path).exists():
                    shutil.copy2(entry.backup_path, entry.original_path)
                    return f"Undone: restored '{entry.original_path}' from backup"
                return "Cannot undo: backup file not found."

            elif op == "create_folder":
                p = Path(entry.path)
                if p.exists() and not any(p.iterdir()):
                    p.rmdir()
                    return f"Undone: removed folder '{entry.path}'"
                return "Cannot undo: folder is not empty."

            elif op == "move_folder":
                shutil.move(entry.path, entry.original_path)
                return f"Undone: moved folder back to '{entry.original_path}'"

            elif op == "rename_folder":
                Path(entry.path).rename(entry.original_path)
                return f"Undone: renamed folder back to '{Path(entry.original_path).name}'"

            else:
                return f"Cannot undo operation type: {op}"

        except Exception as e:
            return f"Undo failed: {e}"

    def get_audit_log(self, lines: int = 50) -> str:
        """Return the last N lines from the audit log."""
        return self._logger.get_recent(lines)
```

---

### services/file_service.py

```python
import shutil
from datetime import datetime
from pathlib import Path
from config.settings import Settings
from utils.path_validator import PathValidator
from utils.logger import AuditLogger
from utils.recycle import RecycleBin
from utils.undo import UndoEntry
from typing import Callable


class FileService:
    """
    Handles all file operations: create, read, write, append,
    copy, move, rename, delete, and file info queries.
    Delegates safety/undo tracking to SafetyService via push_undo callback.
    """

    def __init__(
        self,
        settings: Settings,
        validator: PathValidator,
        logger: AuditLogger,
        recycle: RecycleBin,
        push_undo: Callable[[UndoEntry], None],
        create_undo_backup: Callable[[Path], Path],
    ) -> None:
        self._settings = settings
        self._validator = validator
        self._logger = logger
        self._recycle = recycle
        self._push_undo = push_undo
        self._create_undo_backup = create_undo_backup

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(self, path: str, content: str = "") -> str:
        """Create a new file with optional content."""
        p = self._validator.validate(path)
        if p.exists():
            raise FileExistsError(f"File already exists: {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self._push_undo(UndoEntry("create_file", str(p)))
        self._logger.log("create_file", str(p))
        return f"Created: {p}"

    def read(self, path: str) -> str:
        """Read and return the full text content of a file."""
        p = self._validator.validate(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        content = p.read_text(encoding="utf-8", errors="replace")
        self._logger.log("read_file", str(p))
        return content

    def write(self, path: str, content: str) -> str:
        """Overwrite the full content of an existing file."""
        p = self._validator.validate(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        backup = self._create_undo_backup(p)
        p.write_text(content, encoding="utf-8")
        self._push_undo(UndoEntry("write_file", str(p), original_path=str(p), backup_path=str(backup)))
        self._logger.log("write_file", str(p))
        return f"Written: {p}"

    def append(self, path: str, content: str) -> str:
        """Append content to the end of an existing file."""
        p = self._validator.validate(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        backup = self._create_undo_backup(p)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        self._push_undo(UndoEntry("append_file", str(p), original_path=str(p), backup_path=str(backup)))
        self._logger.log("append_file", str(p))
        return f"Appended to: {p}"

    def copy(self, src: str, dest: str) -> str:
        """Copy a file to a new location."""
        s, d = self._validator.validate_pair(src, dest)
        if not s.is_file():
            raise FileNotFoundError(f"Source not found: {s}")
        shutil.copy2(s, d)
        self._push_undo(UndoEntry("copy_file", str(d)))
        self._logger.log("copy_file", str(s), detail=f"to {d}")
        return f"Copied: {s} → {d}"

    def move(self, src: str, dest: str) -> str:
        """Move a file to a new location."""
        s, d = self._validator.validate_pair(src, dest)
        if not s.is_file():
            raise FileNotFoundError(f"Source not found: {s}")
        shutil.move(str(s), str(d))
        self._push_undo(UndoEntry("move_file", str(d), original_path=str(s)))
        self._logger.log("move_file", str(s), detail=f"to {d}")
        return f"Moved: {s} → {d}"

    def rename(self, path: str, new_name: str) -> str:
        """Rename a file. Provide only the new name, not a full path."""
        p = self._validator.validate(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        new_path = p.parent / new_name
        p.rename(new_path)
        self._push_undo(UndoEntry("rename_file", str(new_path), original_path=str(p)))
        self._logger.log("rename_file", str(p), detail=f"→ {new_name}")
        return f"Renamed: {p.name} → {new_name}"

    def delete(self, path: str) -> str:
        """Delete a file by sending it to the Recycle Bin."""
        p = self._validator.validate(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        backup = self._create_undo_backup(p)
        self._recycle.send(p)
        self._push_undo(UndoEntry("delete_file", str(p), original_path=str(p), backup_path=str(backup)))
        self._logger.log("delete_file", str(p))
        return f"Deleted (sent to Recycle Bin): {p.name}"

    def exists(self, path: str) -> str:
        """Check if a file exists at the given path."""
        try:
            p = self._validator.validate(path)
            status = "EXISTS" if p.exists() else "NOT FOUND"
            self._logger.log("file_exists", str(p), detail=status)
            return f"{status}: {p}"
        except ValueError as e:
            return str(e)

    # ── File Info ─────────────────────────────────────────────────────────

    def get_info(self, path: str) -> str:
        """Return detailed metadata about a file."""
        p = self._validator.validate(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {p}")
        stat = p.stat()
        size = stat.st_size
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        self._logger.log("get_file_info", str(p))
        return (
            f"Name     : {p.name}\n"
            f"Path     : {p}\n"
            f"Extension: {p.suffix or 'none'}\n"
            f"Size     : {size:,} bytes  ({size / 1024:.1f} KB)\n"
            f"Created  : {created}\n"
            f"Modified : {modified}"
        )

    def count(self, folder: str) -> str:
        """Count total files and subfolders inside a directory."""
        p = self._validator.validate(folder)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        files = sum(1 for f in p.rglob("*") if f.is_file())
        folders = sum(1 for f in p.rglob("*") if f.is_dir())
        self._logger.log("count_files", str(p))
        return f"{p.name}: {files} file(s), {folders} subfolder(s)"

    def find_duplicates(self, folder: str) -> str:
        """Find files that share the same name in different locations."""
        p = self._validator.validate(folder)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        seen: dict[str, list[str]] = {}
        for f in p.rglob("*"):
            if f.is_file():
                seen.setdefault(f.name.lower(), []).append(str(f))
        dupes = {name: paths for name, paths in seen.items() if len(paths) > 1}
        self._logger.log("find_duplicates", str(p), detail=f"found={len(dupes)}")
        if not dupes:
            return f"No duplicate filenames found in {p.name}"
        lines = [f"Found {len(dupes)} duplicate filename(s) in {p.name}:"]
        for name, paths in dupes.items():
            lines.append(f"\n📄 {name}")
            lines.extend(f"   {path}" for path in paths)
        return "\n".join(lines)

    def find_large(self, folder: str, min_mb: float = 100) -> str:
        """Find files larger than min_mb megabytes."""
        p = self._validator.validate(folder)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        min_bytes = min_mb * 1024 * 1024
        results = [
            (f.stat().st_size, str(f))
            for f in p.rglob("*")
            if f.is_file() and f.stat().st_size >= min_bytes
        ]
        results.sort(reverse=True)
        self._logger.log("find_large_files", str(p), detail=f"min={min_mb}MB found={len(results)}")
        if not results:
            return f"No files larger than {min_mb}MB in {p.name}"
        lines = [f"Files larger than {min_mb}MB in {p.name}:"]
        lines.extend(f"  {size / 1024**2:.1f} MB  {path}" for size, path in results)
        return "\n".join(lines)

    def find_empty(self, folder: str) -> str:
        """Find files with zero bytes in a folder."""
        p = self._validator.validate(folder)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        results = [str(f) for f in p.rglob("*") if f.is_file() and f.stat().st_size == 0]
        self._logger.log("find_empty_files", str(p), detail=f"found={len(results)}")
        if not results:
            return f"No empty files found in {p.name}"
        return f"Found {len(results)} empty file(s):\n" + "\n".join(results)
```

---

### services/folder_service.py

```python
import shutil
from pathlib import Path
from config.settings import Settings
from utils.path_validator import PathValidator
from utils.logger import AuditLogger
from utils.recycle import RecycleBin
from utils.undo import UndoEntry
from typing import Callable


class FolderService:
    """
    Handles all folder/directory operations: create, list, tree,
    size, copy, move, rename, delete.
    """

    def __init__(
        self,
        settings: Settings,
        validator: PathValidator,
        logger: AuditLogger,
        recycle: RecycleBin,
        push_undo: Callable[[UndoEntry], None],
    ) -> None:
        self._settings = settings
        self._validator = validator
        self._logger = logger
        self._recycle = recycle
        self._push_undo = push_undo

    def create(self, path: str) -> str:
        """Create a new folder including any missing parent folders."""
        p = self._validator.validate(path)
        if p.exists():
            raise FileExistsError(f"Folder already exists: {p}")
        p.mkdir(parents=True)
        self._push_undo(UndoEntry("create_folder", str(p)))
        self._logger.log("create_folder", str(p))
        return f"Created folder: {p}"

    def list_dir(self, path: str) -> str:
        """List all items in a folder. Folders shown first, then files."""
        p = self._validator.validate(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        if not items:
            return f"{p.name} is empty."
        lines = [f"Contents of {p} ({len(items)} items):"]
        lines.extend(
            f"  {'📄' if item.is_file() else '📁'} {item.name}"
            for item in items
        )
        self._logger.log("list_directory", str(p))
        return "\n".join(lines)

    def tree(self, path: str, max_depth: int = 3) -> str:
        """Show a tree view of a folder up to max_depth levels deep."""
        p = self._validator.validate(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        lines = [f"📁 {p.name}"]
        self._build_tree(p, lines, prefix="", depth=0, max_depth=max_depth)
        self._logger.log("folder_tree", str(p))
        return "\n".join(lines)

    def _build_tree(
        self, folder: Path, lines: list[str], prefix: str, depth: int, max_depth: int
    ) -> None:
        """Recursive helper to build the tree lines."""
        if depth >= max_depth:
            return
        items = sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            icon = "📄 " if item.is_file() else "📁 "
            lines.append(f"{prefix}{connector}{icon}{item.name}")
            if item.is_dir():
                extension = "    " if is_last else "│   "
                self._build_tree(item, lines, prefix + extension, depth + 1, max_depth)

    def size(self, path: str) -> str:
        """Return the total size of all files inside a folder."""
        p = self._validator.validate(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        self._logger.log("folder_size", str(p))
        if total < 1024:
            return f"{p.name}: {total} bytes"
        elif total < 1024 ** 2:
            return f"{p.name}: {total / 1024:.1f} KB"
        elif total < 1024 ** 3:
            return f"{p.name}: {total / 1024 ** 2:.1f} MB"
        else:
            return f"{p.name}: {total / 1024 ** 3:.2f} GB"

    def copy(self, src: str, dest: str) -> str:
        """Copy an entire folder to a new location."""
        s, d = self._validator.validate_pair(src, dest)
        if not s.is_dir():
            raise NotADirectoryError(f"Source is not a directory: {s}")
        shutil.copytree(str(s), str(d))
        self._push_undo(UndoEntry("copy_folder", str(d)))
        self._logger.log("copy_folder", str(s), detail=f"to {d}")
        return f"Copied folder: {s.name} → {d}"

    def move(self, src: str, dest: str) -> str:
        """Move a folder to a new location."""
        s, d = self._validator.validate_pair(src, dest)
        if not s.is_dir():
            raise NotADirectoryError(f"Source is not a directory: {s}")
        shutil.move(str(s), str(d))
        self._push_undo(UndoEntry("move_folder", str(d), original_path=str(s)))
        self._logger.log("move_folder", str(s), detail=f"to {d}")
        return f"Moved folder: {s.name} → {d}"

    def rename(self, path: str, new_name: str) -> str:
        """Rename a folder. Provide only the new name, not a full path."""
        p = self._validator.validate(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        new_path = p.parent / new_name
        p.rename(new_path)
        self._push_undo(UndoEntry("rename_folder", str(new_path), original_path=str(p)))
        self._logger.log("rename_folder", str(p), detail=f"→ {new_name}")
        return f"Renamed folder: {p.name} → {new_name}"

    def delete(self, path: str) -> str:
        """Delete a folder by sending it to the Recycle Bin."""
        p = self._validator.validate(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        self._recycle.send(p)
        self._logger.log("delete_folder", str(p))
        return f"Deleted folder (sent to Recycle Bin): {p.name}"
```

---

### services/search_service.py

```python
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
```

---

### tools/file_ops.py

```python
from fastmcp import FastMCP
from services.file_service import FileService


class FileOpsTools:
    """
    MCP tool registrar for file CRUD operations.
    Thin layer: validates nothing, delegates everything to FileService.
    """

    def __init__(self, service: FileService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all file operation tools onto the MCP server."""
        service = self._service  # captured by closures below

        @mcp.tool()
        def create_file(path: str, content: str = "") -> str:
            """
            Create a new file at the given path.
            Content is optional — omit it to create an empty file.
            Example: create_file('C:/Users/Me/Desktop/notes.txt', 'Hello!')
            """
            return service.create(path, content)

        @mcp.tool()
        def read_file(path: str) -> str:
            """
            Read and return the full text content of a file.
            Example: read_file('C:/Users/Me/Desktop/notes.txt')
            """
            return service.read(path)

        @mcp.tool()
        def write_file(path: str, content: str) -> str:
            """
            Overwrite the content of an existing file.
            Warning: replaces all existing content.
            Example: write_file('C:/Users/Me/Desktop/notes.txt', 'New content')
            """
            return service.write(path, content)

        @mcp.tool()
        def append_file(path: str, content: str) -> str:
            """
            Append text to the end of an existing file without erasing it.
            Example: append_file('C:/Users/Me/Desktop/log.txt', 'new line\\n')
            """
            return service.append(path, content)

        @mcp.tool()
        def copy_file(src: str, dest: str) -> str:
            """
            Copy a file from src to dest.
            Example: copy_file('C:/Users/Me/Desktop/a.txt', 'C:/Users/Me/Documents/a.txt')
            """
            return service.copy(src, dest)

        @mcp.tool()
        def move_file(src: str, dest: str) -> str:
            """
            Move a file from src to dest.
            Example: move_file('C:/Users/Me/Desktop/a.txt', 'C:/Users/Me/Documents/a.txt')
            """
            return service.move(src, dest)

        @mcp.tool()
        def rename_file(path: str, new_name: str) -> str:
            """
            Rename a file. Provide only the new filename, not a full path.
            Example: rename_file('C:/Users/Me/Desktop/old.txt', 'new.txt')
            """
            return service.rename(path, new_name)

        @mcp.tool()
        def delete_file(path: str) -> str:
            """
            Delete a file by sending it to the Recycle Bin (not permanent).
            Always call confirm_delete first to review before deleting.
            Example: delete_file('C:/Users/Me/Desktop/old.txt')
            """
            return service.delete(path)

        @mcp.tool()
        def file_exists(path: str) -> str:
            """
            Check whether a file exists at the given path.
            Example: file_exists('C:/Users/Me/Desktop/notes.txt')
            """
            return service.exists(path)
```

---

### tools/folder_ops.py

```python
from fastmcp import FastMCP
from services.folder_service import FolderService


class FolderOpsTools:
    """
    MCP tool registrar for folder/directory operations.
    """

    def __init__(self, service: FolderService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all folder operation tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def create_folder(path: str) -> str:
            """
            Create a new folder. Creates parent folders too if needed.
            Example: create_folder('C:/Users/Me/Desktop/NewProject')
            """
            return service.create(path)

        @mcp.tool()
        def list_directory(path: str) -> str:
            """
            List all files and subfolders inside a directory.
            Example: list_directory('C:/Users/Me/Desktop')
            """
            return service.list_dir(path)

        @mcp.tool()
        def folder_tree(path: str, max_depth: int = 3) -> str:
            """
            Show a tree view of a folder up to max_depth levels deep.
            Example: folder_tree('C:/Users/Me/Documents', max_depth=2)
            """
            return service.tree(path, max_depth)

        @mcp.tool()
        def folder_size(path: str) -> str:
            """
            Return the total size of all files inside a folder.
            Example: folder_size('C:/Users/Me/Downloads')
            """
            return service.size(path)

        @mcp.tool()
        def copy_folder(src: str, dest: str) -> str:
            """
            Copy an entire folder and its contents to a new location.
            Example: copy_folder('C:/Users/Me/Desktop/Project', 'C:/Users/Me/Documents/Project')
            """
            return service.copy(src, dest)

        @mcp.tool()
        def move_folder(src: str, dest: str) -> str:
            """
            Move a folder to a new location.
            Example: move_folder('C:/Users/Me/Desktop/Old', 'C:/Users/Me/Documents/Old')
            """
            return service.move(src, dest)

        @mcp.tool()
        def rename_folder(path: str, new_name: str) -> str:
            """
            Rename a folder. Provide only the new name, not a full path.
            Example: rename_folder('C:/Users/Me/Desktop/OldName', 'NewName')
            """
            return service.rename(path, new_name)

        @mcp.tool()
        def delete_folder(path: str) -> str:
            """
            Delete a folder by sending it to the Recycle Bin.
            Always call confirm_delete first to review before deleting.
            Example: delete_folder('C:/Users/Me/Desktop/OldFolder')
            """
            return service.delete(path)
```

---

### tools/search_ops.py

```python
from fastmcp import FastMCP
from services.search_service import SearchService


class SearchOpsTools:
    """
    MCP tool registrar for search operations.
    """

    def __init__(self, service: SearchService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all search tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def search_by_name(folder: str, name: str) -> str:
            """
            Search for files whose name contains the given string.
            Case-insensitive. Searches recursively.
            Example: search_by_name('C:/Users/Me/Documents', 'resume')
            """
            return service.by_name(folder, name)

        @mcp.tool()
        def search_by_extension(folder: str, ext: str) -> str:
            """
            Find all files with a given extension inside a folder.
            Example: search_by_extension('C:/Users/Me/Documents', '.pdf')
            """
            return service.by_extension(folder, ext)

        @mcp.tool()
        def search_by_date(folder: str, days: int = 7) -> str:
            """
            Find files modified within the last N days.
            Default is 7 days. Results sorted newest first.
            Example: search_by_date('C:/Users/Me/Desktop', days=3)
            """
            return service.by_date(folder, days)

        @mcp.tool()
        def search_by_size(folder: str, min_mb: float = 0.0, max_mb: float = 9999.0) -> str:
            """
            Find files between min_mb and max_mb megabytes in size.
            Example: search_by_size('C:/Users/Me/Downloads', min_mb=10, max_mb=500)
            """
            return service.by_size(folder, min_mb, max_mb)
```

---

### tools/file_info.py

```python
from fastmcp import FastMCP
from services.file_service import FileService


class FileInfoTools:
    """
    MCP tool registrar for file information and analysis tools.
    """

    def __init__(self, service: FileService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all file info tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def get_file_info(path: str) -> str:
            """
            Get detailed metadata about a file: name, size, created date, modified date.
            Example: get_file_info('C:/Users/Me/Desktop/report.pdf')
            """
            return service.get_info(path)

        @mcp.tool()
        def count_files(folder: str) -> str:
            """
            Count the total number of files and subfolders in a directory.
            Example: count_files('C:/Users/Me/Documents')
            """
            return service.count(folder)

        @mcp.tool()
        def find_duplicates(folder: str) -> str:
            """
            Find files that share the same filename in different locations.
            Example: find_duplicates('C:/Users/Me/Documents')
            """
            return service.find_duplicates(folder)

        @mcp.tool()
        def find_large_files(folder: str, min_mb: float = 100.0) -> str:
            """
            Find all files larger than min_mb megabytes.
            Default threshold is 100 MB.
            Example: find_large_files('C:/Users/Me/Downloads', min_mb=50)
            """
            return service.find_large(folder, min_mb)

        @mcp.tool()
        def find_empty_files(folder: str) -> str:
            """
            Find all files with zero bytes inside a folder.
            Example: find_empty_files('C:/Users/Me/Desktop')
            """
            return service.find_empty(folder)
```

---

### tools/safety_ops.py

```python
from fastmcp import FastMCP
from services.safety_service import SafetyService


class SafetyOpsTools:
    """
    MCP tool registrar for safety operations: backup, undo, confirm, audit.
    """

    def __init__(self, service: SafetyService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all safety tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def confirm_delete(path: str) -> str:
            """
            Show file details before deleting. Always call this before delete_file or delete_folder.
            Returns name, size, and last modified date so the user can confirm.
            Example: confirm_delete('C:/Users/Me/Desktop/old_file.txt')
            """
            return service.confirm_delete(path)

        @mcp.tool()
        def backup_file(path: str) -> str:
            """
            Create a backup copy of a file in the backups/ directory.
            Useful before making big changes to important files.
            Example: backup_file('C:/Users/Me/Documents/important.docx')
            """
            return service.backup_file(path)

        @mcp.tool()
        def undo_last() -> str:
            """
            Reverse the last file operation.
            Supports: create, copy, move, rename, delete, write, append.
            Example: undo_last()
            """
            return service.undo_last()

        @mcp.tool()
        def get_audit_log(lines: int = 50) -> str:
            """
            Return the last N lines from the audit log.
            Default is 50 lines. Shows every operation AXON has performed.
            Example: get_audit_log(lines=100)
            """
            return service.get_audit_log(lines)
```

---

### main.py

```python
from fastmcp import FastMCP
from config.settings import get_settings
from utils.path_validator import PathValidator
from utils.logger import AuditLogger
from utils.recycle import RecycleBin
from services.file_service import FileService
from services.folder_service import FolderService
from services.search_service import SearchService
from services.safety_service import SafetyService
from tools.file_ops import FileOpsTools
from tools.folder_ops import FolderOpsTools
from tools.search_ops import SearchOpsTools
from tools.file_info import FileInfoTools
from tools.safety_ops import SafetyOpsTools


class ServiceFactory:
    """
    Factory that creates and wires all application services.
    Handles dependency injection so main.py stays clean.
    """

    @staticmethod
    def create_all() -> tuple[FileService, FolderService, SearchService, SafetyService]:
        """
        Factory method: instantiate all services with correct dependencies.
        Returns all services as a tuple.
        """
        settings = get_settings()
        validator = PathValidator(settings)
        logger = AuditLogger.get_instance(settings)
        recycle = RecycleBin()

        safety = SafetyService(settings, validator, logger, recycle)

        file_svc = FileService(
            settings=settings,
            validator=validator,
            logger=logger,
            recycle=recycle,
            push_undo=safety.push_undo,
            create_undo_backup=safety.create_undo_backup,
        )
        folder_svc = FolderService(
            settings=settings,
            validator=validator,
            logger=logger,
            recycle=recycle,
            push_undo=safety.push_undo,
        )
        search_svc = SearchService(validator=validator, logger=logger)

        return file_svc, folder_svc, search_svc, safety


class MCPServerFactory:
    """
    Factory that builds the fully configured AXON MCP server.
    Creates all services, registers all tools, returns a ready server.
    """

    @staticmethod
    def create() -> FastMCP:
        """
        Factory method: wire services and tools, return the MCP server.
        """
        mcp = FastMCP(
            name="AXON",
            instructions=(
                "You are AXON — an autonomous file system agent.\n"
                "You have full access to the user's Windows file system "
                "within the configured allowed paths.\n\n"
                "Rules:\n"
                "1. Always call confirm_delete before any delete operation.\n"
                "2. Use backup_file before overwriting important files.\n"
                "3. Use undo_last if you make a mistake.\n"
                "4. Only operate within allowed paths — never guess paths.\n"
                "5. If unsure about a path, use file_exists first.\n"
            ),
        )

        file_svc, folder_svc, search_svc, safety_svc = ServiceFactory.create_all()

        FileOpsTools(file_svc).register(mcp)
        FolderOpsTools(folder_svc).register(mcp)
        SearchOpsTools(search_svc).register(mcp)
        FileInfoTools(file_svc).register(mcp)
        SafetyOpsTools(safety_svc).register(mcp)

        return mcp


if __name__ == "__main__":
    server = MCPServerFactory.create()
    print("AXON MCP Server started. 30 tools ready.")
    server.run()
```

---

### tools/__init__.py

```python
from tools.file_ops import FileOpsTools
from tools.folder_ops import FolderOpsTools
from tools.search_ops import SearchOpsTools
from tools.file_info import FileInfoTools
from tools.safety_ops import SafetyOpsTools

__all__ = [
    "FileOpsTools",
    "FolderOpsTools",
    "SearchOpsTools",
    "FileInfoTools",
    "SafetyOpsTools",
]
```

### services/__init__.py

```python
from services.file_service import FileService
from services.folder_service import FolderService
from services.search_service import SearchService
from services.safety_service import SafetyService

__all__ = ["FileService", "FolderService", "SearchService", "SafetyService"]
```

### utils/__init__.py

```python
from utils.path_validator import PathValidator
from utils.logger import AuditLogger
from utils.recycle import RecycleBin
from utils.undo import UndoEntry

__all__ = ["PathValidator", "AuditLogger", "RecycleBin", "UndoEntry"]
```

### config/__init__.py

```python
from config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

---

### tests/test_file_ops.py

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from services.file_service import FileService


@pytest.fixture
def mock_service(tmp_path):
    """Create a FileService pointing to a temp directory."""
    from config.settings import Settings
    from utils.path_validator import PathValidator
    from utils.logger import AuditLogger
    from utils.recycle import RecycleBin

    settings = Settings(
        allowed_paths=(tmp_path,),
        backup_dir=tmp_path / "backups",
        log_file=tmp_path / "logs" / "audit.log",
        undo_stack_file=tmp_path / "logs" / "undo.json",
    )
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    (settings.backup_dir / "undo").mkdir(parents=True, exist_ok=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    validator = PathValidator(settings)
    logger = MagicMock()
    recycle = MagicMock()
    push_undo = MagicMock()
    create_undo_backup = MagicMock(return_value=tmp_path / "backups" / "undo" / "test_backup.txt")

    return FileService(settings, validator, logger, recycle, push_undo, create_undo_backup)


def test_create_and_read(mock_service, tmp_path):
    path = str(tmp_path / "test.txt")
    mock_service.create(path, "hello world")
    content = mock_service.read(path)
    assert content == "hello world"


def test_create_empty_file(mock_service, tmp_path):
    path = str(tmp_path / "empty.txt")
    result = mock_service.create(path)
    assert Path(path).exists()
    assert "Created" in result


def test_file_exists(mock_service, tmp_path):
    path = str(tmp_path / "exists.txt")
    mock_service.create(path)
    result = mock_service.exists(path)
    assert "EXISTS" in result


def test_rename_file(mock_service, tmp_path):
    path = str(tmp_path / "original.txt")
    mock_service.create(path)
    mock_service.rename(path, "renamed.txt")
    assert Path(tmp_path / "renamed.txt").exists()
    assert not Path(path).exists()
```

---

## Step 7 — Write README.md

```markdown
# AXON 🤖

**A = Autonomous | X = eXtensible | O = OS | N = Navigator**

AXON is a local MCP (Model Context Protocol) server that gives any LLM
full structured control over your Windows file system.
100% local. No cloud. No API costs. Your data never leaves your machine.

---

## Architecture

Built with **Clean Architecture** — strict separation of concerns:

```
tools/      ← MCP interface layer    (what the LLM sees and calls)
services/   ← Business logic layer   (how operations actually work)
utils/      ← Infrastructure layer   (validation, logging, recycle bin)
config/     ← Configuration layer    (settings, environment)
```

Design patterns used:
- **Factory Method** — `Settings.from_env()`, `AuditLogger.get_instance()`, `MCPServerFactory.create()`
- **Dependency Injection** — all services receive dependencies via constructor
- **Singleton** — one Settings instance, one AuditLogger per process
- **Single Responsibility** — each class has exactly one reason to change

---

## Tools (30 total)

| Category | Tools |
|---|---|
| File Operations | create, read, write, append, copy, move, rename, delete, exists |
| Folder Operations | create, list, tree, size, copy, move, rename, delete |
| Search | by name, by extension, by date, by size |
| File Info | get info, count, find duplicates, find large, find empty |
| Safety | confirm delete, backup, undo last, audit log |

---

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| fastmcp | 4.1.4 | MCP server framework |
| send2trash | 2.1.0 | Safe delete via Recycle Bin |
| python-dotenv | 1.0.1 | Environment config |
| Python | >= 3.10 | Runtime |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/AXON.git
cd axon

# 2. Install dependencies
uv sync

# 3. Configure allowed paths
# Edit .env — set ALLOWED_PATHS to your folders

# 4. Run the server
uv run python main.py
```

---

## Safety Features

- All paths validated against `ALLOWED_PATHS` before every operation
- Deletes go to Recycle Bin — never permanent
- Undo stack with JSON persistence — `undo_last()` reverses any operation
- Full audit log at `logs/audit.log` — every operation recorded
- Confirm before delete — `confirm_delete()` shows file details first

---

## Roadmap

- [x] Phase 1 — File System MCP Server (30 tools)
- [ ] Phase 2 — Obsidian Vault Integration (semantic search)
- [ ] Phase 3 — Windows System Control (processes, clipboard, notifications)
- [ ] Phase 4 — Local LLM Agent (Ollama integration)
- [ ] Phase 5 — Voice Input (Whisper)

---

*Built on FastMCP · Clean Architecture · 100% Local*
```

---

## Step 8 — Verify Setup

Run:

```bash
uv run python main.py
```

Expected output:
```
AXON MCP Server started. 30 tools ready.
```

If any import fails, check:
1. All `__init__.py` files exist
2. `.env` file has valid `ALLOWED_PATHS`
3. `uv add` completed without errors

---

## Done ✅

AXON MCP server is scaffolded and ready.
All 30 tools are implemented and registered.
Next step: connect to any MCP-compatible LLM client and start testing.
