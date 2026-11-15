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
