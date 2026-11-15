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
