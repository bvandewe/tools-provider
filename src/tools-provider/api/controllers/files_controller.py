"""Files controller for workspace file downloads and uploads.

This controller provides endpoints for users to:
1. Download files created by agents (reports, exports, etc.)
2. Upload files for agents to process

Files are stored in a per-user workspace directory with automatic cleanup
after 24 hours. This is designed for temporary deliverables, not long-term storage.

Security:
- All endpoints require authentication
- Files are isolated per user (user_id from JWT)
- Path traversal attacks are prevented
- File size limits enforced (10MB upload, 50MB download)
"""

import logging
import mimetypes
import os
import tempfile
from datetime import UTC, datetime, timedelta

from classy_fastapi.decorators import get, post
from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from api.dependencies import get_current_user

log = logging.getLogger(__name__)

# Configuration
WORKSPACE_BASE_DIR = os.path.join(tempfile.gettempdir(), "agent_workspace")
WORKSPACE_FILE_TTL_HOURS = 24
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_DOWNLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Allowed file extensions for upload
ALLOWED_UPLOAD_EXTENSIONS = {
    # Text files
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    # Documents
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    # Code
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    # Archives
    ".zip",
}


def get_user_workspace_dir(user_id: str) -> str:
    """Get workspace directory for a specific user.

    Creates the directory if it doesn't exist.

    Args:
        user_id: User identifier from JWT 'sub' claim

    Returns:
        Path to user's workspace directory
    """
    # Sanitize user_id to prevent path traversal
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
    if not safe_user_id:
        safe_user_id = "anonymous"

    workspace_dir = os.path.join(WORKSPACE_BASE_DIR, safe_user_id)
    os.makedirs(workspace_dir, exist_ok=True)
    return workspace_dir


def validate_filename(filename: str) -> str:
    """Validate and sanitize a filename.

    Args:
        filename: The filename to validate

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If filename is invalid
    """
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    # Prevent path traversal
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename: path traversal not allowed")

    # Extract just the filename (no subdirectories for security)
    safe_filename = os.path.basename(filename)
    if not safe_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    return safe_filename


class FilesController(ControllerBase):
    """Controller for workspace file operations.

    Provides endpoints for downloading and uploading files to the agent workspace.
    Files are temporary (24h TTL) and isolated per user.

    **Important**: Files served by this API are temporary and will be automatically
    deleted after 24 hours. URLs should not be shared externally or used for
    long-term storage.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get(
        "/{filename:path}",
        summary="Download a file from workspace",
        description="""Download a file created by an agent or previously uploaded.

**⚠️ Temporary Files**: Files are automatically deleted after 24 hours.
Do not share these URLs externally or rely on them for permanent storage.

The response includes:
- `X-File-Expires`: ISO timestamp when the file will be deleted
- `X-File-Temporary`: Always "true" to indicate ephemeral nature
""",
        responses={
            200: {"description": "File content"},
            404: {"description": "File not found"},
            401: {"description": "Not authenticated"},
        },
    )
    async def download_file(
        self,
        filename: str,
        user: dict = Depends(get_current_user),
    ) -> FileResponse:
        """Download a file from the user's workspace.

        Args:
            filename: Name of the file to download
            user: Authenticated user from JWT/session

        Returns:
            FileResponse with the file content
        """
        user_id = user.get("sub", "anonymous")
        safe_filename = validate_filename(filename)

        workspace_dir = get_user_workspace_dir(user_id)
        file_path = os.path.join(workspace_dir, safe_filename)

        # Check file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {safe_filename}")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_DOWNLOAD_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File too large ({file_size} bytes). Maximum: {MAX_DOWNLOAD_SIZE_BYTES} bytes")

        # Calculate expiry time based on file modification time
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=UTC)
        expires_at = file_mtime + timedelta(hours=WORKSPACE_FILE_TTL_HOURS)

        # Determine content type
        content_type, _ = mimetypes.guess_type(safe_filename)
        if content_type is None:
            content_type = "application/octet-stream"

        log.info(f"Serving file: {safe_filename} ({file_size} bytes) for user {user_id}")

        return FileResponse(
            path=file_path,
            filename=safe_filename,
            media_type=content_type,
            headers={
                "X-File-Temporary": "true",
                "X-File-Expires": expires_at.isoformat(),
                "X-File-TTL-Hours": str(WORKSPACE_FILE_TTL_HOURS),
                "Cache-Control": "private, no-cache, no-store, must-revalidate",
            },
        )

    @get(
        "/",
        summary="List files in workspace",
        description="""List all files in the user's workspace with metadata.

Returns file names, sizes, and expiry times. Files are automatically
deleted after 24 hours from creation.
""",
    )
    async def list_files(
        self,
        user: dict = Depends(get_current_user),
    ) -> dict:
        """List all files in the user's workspace.

        Args:
            user: Authenticated user from JWT/session

        Returns:
            List of files with metadata
        """
        user_id = user.get("sub", "anonymous")
        workspace_dir = get_user_workspace_dir(user_id)

        files = []
        now = datetime.now(UTC)

        if os.path.exists(workspace_dir):
            for filename in os.listdir(workspace_dir):
                file_path = os.path.join(workspace_dir, filename)
                if os.path.isfile(file_path):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=UTC)
                    expires_at = file_mtime + timedelta(hours=WORKSPACE_FILE_TTL_HOURS)
                    time_remaining = expires_at - now

                    files.append(
                        {
                            "filename": filename,
                            "size_bytes": os.path.getsize(file_path),
                            "created_at": file_mtime.isoformat(),
                            "expires_at": expires_at.isoformat(),
                            "hours_remaining": max(0, time_remaining.total_seconds() / 3600),
                        }
                    )

        return {
            "files": files,
            "count": len(files),
            "workspace_ttl_hours": WORKSPACE_FILE_TTL_HOURS,
            "note": "Files are temporary and will be automatically deleted after 24 hours.",
        }

    @post(
        "/upload",
        summary="Upload a file to workspace",
        description="""Upload a file for agent processing.

The uploaded file will be available to agents via the `file_reader` tool.
Files are stored temporarily (24h TTL) in your personal workspace.

**Limits**:
- Maximum file size: 10MB
- Allowed extensions: txt, md, json, csv, pdf, xlsx, docx, png, jpg, etc.
""",
        responses={
            200: {"description": "File uploaded successfully"},
            400: {"description": "Invalid file"},
            413: {"description": "File too large"},
            401: {"description": "Not authenticated"},
        },
    )
    async def upload_file(
        self,
        file: UploadFile = File(..., description="File to upload"),
        user: dict = Depends(get_current_user),
    ) -> JSONResponse:
        """Upload a file to the user's workspace.

        Args:
            file: The file to upload
            user: Authenticated user from JWT/session

        Returns:
            Upload confirmation with file details
        """
        user_id = user.get("sub", "anonymous")

        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

        safe_filename = validate_filename(file.filename)

        # Validate extension
        ext = os.path.splitext(safe_filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File extension '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}")

        # Read file content with size limit
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File too large ({len(content)} bytes). Maximum: {MAX_UPLOAD_SIZE_BYTES} bytes (10MB)")

        # Save to workspace
        workspace_dir = get_user_workspace_dir(user_id)
        file_path = os.path.join(workspace_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate expiry
        expires_at = datetime.now(UTC) + timedelta(hours=WORKSPACE_FILE_TTL_HOURS)

        log.info(f"Uploaded file: {safe_filename} ({len(content)} bytes) for user {user_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "filename": safe_filename,
                "size_bytes": len(content),
                "content_type": file.content_type,
                "expires_at": expires_at.isoformat(),
                "ttl_hours": WORKSPACE_FILE_TTL_HOURS,
                "message": f"File uploaded successfully. Use file_reader('{safe_filename}') to read it.",
                "note": "This file is temporary and will be deleted after 24 hours.",
            },
        )
