from fastmcp import FastMCP
from services.folder_service import FolderService


class FolderOpsTools:
    """
    MCP tool registrar for folder/directory operations.
    """

    def __init__(self, service: FolderService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all folder operation tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def create_folder(path: str) -> str:
            """
            Create a new folder. Creates parent folders too if needed.
            Example: create_folder('C:/Users/Me/Desktop/NewProject')
            """
            return service.create(path)

        @mcp.tool()
        def list_directory(path: str) -> str:
            """
            List all files and subfolders inside a directory.
            Example: list_directory('C:/Users/Me/Desktop')
            """
            return service.list_dir(path)

        @mcp.tool()
        def folder_tree(path: str, max_depth: int = 3) -> str:
            """
            Show a tree view of a folder up to max_depth levels deep.
            Example: folder_tree('C:/Users/Me/Documents', max_depth=2)
            """
            return service.tree(path, max_depth)

        @mcp.tool()
        def folder_size(path: str) -> str:
            """
            Return the total size of all files inside a folder.
            Example: folder_size('C:/Users/Me/Downloads')
            """
            return service.size(path)

        @mcp.tool()
        def copy_folder(src: str, dest: str) -> str:
            """
            Copy an entire folder and its contents to a new location.
            Example: copy_folder('C:/Users/Me/Desktop/Project', 'C:/Users/Me/Documents/Project')
            """
            return service.copy(src, dest)

        @mcp.tool()
        def move_folder(src: str, dest: str) -> str:
            """
            Move a folder to a new location.
            Example: move_folder('C:/Users/Me/Desktop/Old', 'C:/Users/Me/Documents/Old')
            """
            return service.move(src, dest)

        @mcp.tool()
        def rename_folder(path: str, new_name: str) -> str:
            """
            Rename a folder. Provide only the new name, not a full path.
            Example: rename_folder('C:/Users/Me/Desktop/OldName', 'NewName')
            """
            return service.rename(path, new_name)

        @mcp.tool()
        def delete_folder(path: str) -> str:
            """
            Delete a folder by sending it to the Recycle Bin.
            Always call confirm_delete first to review before deleting.
            Example: delete_folder('C:/Users/Me/Desktop/OldFolder')
            """
            return service.delete(path)
