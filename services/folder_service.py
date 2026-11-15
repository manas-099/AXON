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
