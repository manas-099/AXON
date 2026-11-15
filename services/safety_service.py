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
