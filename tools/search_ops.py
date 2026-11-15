from fastmcp import FastMCP
from services.search_service import SearchService


class SearchOpsTools:
    """
    MCP tool registrar for search operations.
    """

    def __init__(self, service: SearchService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all search tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def search_by_name(folder: str, name: str) -> str:
            """
            Search for files whose name contains the given string.
            Case-insensitive. Searches recursively.
            Example: search_by_name('C:/Users/Me/Documents', 'resume')
            """
            return service.by_name(folder, name)

        @mcp.tool()
        def search_by_extension(folder: str, ext: str) -> str:
            """
            Find all files with a given extension inside a folder.
            Example: search_by_extension('C:/Users/Me/Documents', '.pdf')
            """
            return service.by_extension(folder, ext)

        @mcp.tool()
        def search_by_date(folder: str, days: int = 7) -> str:
            """
            Find files modified within the last N days.
            Default is 7 days. Results sorted newest first.
            Example: search_by_date('C:/Users/Me/Desktop', days=3)
            """
            return service.by_date(folder, days)

        @mcp.tool()
        def search_by_size(folder: str, min_mb: float = 0.0, max_mb: float = 9999.0) -> str:
            """
            Find files between min_mb and max_mb megabytes in size.
            Example: search_by_size('C:/Users/Me/Downloads', min_mb=10, max_mb=500)
            """
            return service.by_size(folder, min_mb, max_mb)
