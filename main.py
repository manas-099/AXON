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
