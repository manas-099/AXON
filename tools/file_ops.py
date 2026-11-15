from fastmcp import FastMCP
from services.file_service import FileService


class FileOpsTools:
    """
    MCP tool registrar for file CRUD operations.
    Thin layer: validates nothing, delegates everything to FileService.
    """

    def __init__(self, service: FileService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all file operation tools onto the MCP server."""
        service = self._service  # captured by closures below

        @mcp.tool()
        def create_file(path: str, content: str = "") -> str:
            """
            Create a new file at the given path.
            Content is optional — omit it to create an empty file.
            Example: create_file('C:/Users/Me/Desktop/notes.txt', 'Hello!')
            """
            return service.create(path, content)

        @mcp.tool()
        def read_file(path: str) -> str:
            """
            Read and return the full text content of a file.
            Example: read_file('C:/Users/Me/Desktop/notes.txt')
            """
            return service.read(path)

        @mcp.tool()
        def write_file(path: str, content: str) -> str:
            """
            Overwrite the content of an existing file.
            Warning: replaces all existing content.
            Example: write_file('C:/Users/Me/Desktop/notes.txt', 'New content')
            """
            return service.write(path, content)

        @mcp.tool()
        def append_file(path: str, content: str) -> str:
            """
            Append text to the end of an existing file without erasing it.
            Example: append_file('C:/Users/Me/Desktop/log.txt', 'new line\\n')
            """
            return service.append(path, content)

        @mcp.tool()
        def copy_file(src: str, dest: str) -> str:
            """
            Copy a file from src to dest.
            Example: copy_file('C:/Users/Me/Desktop/a.txt', 'C:/Users/Me/Documents/a.txt')
            """
            return service.copy(src, dest)

        @mcp.tool()
        def move_file(src: str, dest: str) -> str:
            """
            Move a file from src to dest.
            Example: move_file('C:/Users/Me/Desktop/a.txt', 'C:/Users/Me/Documents/a.txt')
            """
            return service.move(src, dest)

        @mcp.tool()
        def rename_file(path: str, new_name: str) -> str:
            """
            Rename a file. Provide only the new filename, not a full path.
            Example: rename_file('C:/Users/Me/Desktop/old.txt', 'new.txt')
            """
            return service.rename(path, new_name)

        @mcp.tool()
        def delete_file(path: str) -> str:
            """
            Delete a file by sending it to the Recycle Bin (not permanent).
            Always call confirm_delete first to review before deleting.
            Example: delete_file('C:/Users/Me/Desktop/old.txt')
            """
            return service.delete(path)

        @mcp.tool()
        def file_exists(path: str) -> str:
            """
            Check whether a file exists at the given path.
            Example: file_exists('C:/Users/Me/Desktop/notes.txt')
            """
            return service.exists(path)
