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
