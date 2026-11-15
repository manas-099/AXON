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
