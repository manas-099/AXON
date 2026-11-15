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
