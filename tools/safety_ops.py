from fastmcp import FastMCP
from services.safety_service import SafetyService


class SafetyOpsTools:
    """
    MCP tool registrar for safety operations: backup, undo, confirm, audit.
    """

    def __init__(self, service: SafetyService) -> None:
        self._service = service

    def register(self, mcp: FastMCP) -> None:
        """Register all safety tools onto the MCP server."""
        service = self._service

        @mcp.tool()
        def confirm_delete(path: str) -> str:
            """
            Show file details before deleting. Always call this before delete_file or delete_folder.
            Returns name, size, and last modified date so the user can confirm.
            Example: confirm_delete('C:/Users/Me/Desktop/old_file.txt')
            """
            return service.confirm_delete(path)

        @mcp.tool()
        def backup_file(path: str) -> str:
            """
            Create a backup copy of a file in the backups/ directory.
            Useful before making big changes to important files.
            Example: backup_file('C:/Users/Me/Documents/important.docx')
            """
            return service.backup_file(path)

        @mcp.tool()
        def undo_last() -> str:
            """
            Reverse the last file operation.
            Supports: create, copy, move, rename, delete, write, append.
            Example: undo_last()
            """
            return service.undo_last()

        @mcp.tool()
        def get_audit_log(lines: int = 50) -> str:
            """
            Return the last N lines from the audit log.
            Default is 50 lines. Shows every operation AXON has performed.
            Example: get_audit_log(lines=100)
            """
            return service.get_audit_log(lines)
