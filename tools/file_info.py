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
