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
