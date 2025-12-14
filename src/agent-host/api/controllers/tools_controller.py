"""Tools proxy controller for forwarding requests to tools-provider.

This controller proxies requests from the agent-host UI to the tools-provider
backend, allowing the UI to access tools-provider endpoints through the same
origin (avoiding CORS issues).

Routes:
    /api/tools/files/upload -> tools-provider /api/files/upload
    /api/tools/files/{filename} -> tools-provider /api/files/{filename}
    /api/tools/files/ -> tools-provider /api/files/
"""

import logging

import httpx
from classy_fastapi.decorators import delete, get, post
from fastapi import Depends, File, HTTPException, Request, Response, UploadFile, status
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from api.dependencies import get_current_user
from application.settings import app_settings

log = logging.getLogger(__name__)

# Timeout for proxied requests
PROXY_TIMEOUT = 30.0


class ToolsController(ControllerBase):
    """Controller that proxies /api/tools/* requests to tools-provider.

    This enables the agent-host UI to access tools-provider endpoints
    like /api/files/* through the same origin, maintaining session
    cookies and avoiding CORS issues.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self._tools_provider_url = app_settings.tools_provider_url

    async def _proxy_request(
        self,
        request: Request,
        path: str,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
        user: dict | None = None,
    ) -> Response:
        """Proxy a request to tools-provider.

        Args:
            request: The incoming FastAPI request
            path: The path to proxy to (e.g., "/api/files/upload")
            method: HTTP method
            body: Request body bytes
            content_type: Content-Type header value
            user: Authenticated user dict (for logging/auth forwarding)

        Returns:
            Response from tools-provider
        """
        url = f"{self._tools_provider_url}{path}"

        # Forward relevant headers
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        # Forward authorization if present
        if auth_header := request.headers.get("Authorization"):
            headers["Authorization"] = auth_header

        # Forward cookies for session auth
        if cookie := request.headers.get("Cookie"):
            headers["Cookie"] = cookie

        log.debug(f"Proxying {method} to {url}")

        try:
            async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    content=body,
                    headers=headers,
                )

                # Build response with relevant headers
                response_headers = {}
                for header in ["Content-Type", "Content-Disposition", "X-File-Expires", "X-File-Temporary"]:
                    if value := response.headers.get(header):
                        response_headers[header] = value

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Request to tools-provider timed out")
        except httpx.RequestError as e:
            log.error(f"Proxy request failed: {e}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to connect to tools-provider: {str(e)}")

    @post(
        "/files/upload",
        summary="Proxy file upload to tools-provider",
        description="Forwards file uploads to tools-provider /api/files/upload",
    )
    async def proxy_upload(
        self,
        request: Request,
        file: UploadFile = File(...),
        user: dict = Depends(get_current_user),
    ) -> Response:
        """Proxy file upload to tools-provider.

        This endpoint handles multipart file uploads and forwards them
        to the tools-provider files endpoint.
        """
        content = await file.read()
        url = f"{self._tools_provider_url}/api/files/upload"

        headers = {}
        if auth_header := request.headers.get("Authorization"):
            headers["Authorization"] = auth_header
        if cookie := request.headers.get("Cookie"):
            headers["Cookie"] = cookie

        log.debug(f"Proxying file upload to {url}, file: {file.filename}, size: {len(content)}")

        try:
            async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
                files = {"file": (file.filename, content, file.content_type or "application/octet-stream")}
                response = await client.post(url=url, files=files, headers=headers)

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers={"Content-Type": response.headers.get("Content-Type", "application/json")},
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File upload to tools-provider timed out")
        except httpx.RequestError as e:
            log.error(f"File upload proxy failed: {e}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to upload file: {str(e)}")

    @get(
        "/files/",
        summary="List files in user's workspace",
        description="Forwards request to tools-provider /api/files/",
    )
    async def proxy_list_files(
        self,
        request: Request,
        user: dict = Depends(get_current_user),
    ) -> Response:
        """Proxy list files request to tools-provider."""
        return await self._proxy_request(request=request, path="/api/files/", method="GET", user=user)

    @get(
        "/files/{filename:path}",
        summary="Download a file from workspace",
        description="Forwards download request to tools-provider /api/files/{filename}",
    )
    async def proxy_download(
        self,
        filename: str,
        request: Request,
        user: dict = Depends(get_current_user),
    ) -> Response:
        """Proxy file download request to tools-provider."""
        return await self._proxy_request(request=request, path=f"/api/files/{filename}", method="GET", user=user)

    @delete(
        "/files/{filename:path}",
        summary="Delete a file from workspace",
        description="Forwards delete request to tools-provider /api/files/{filename}",
    )
    async def proxy_delete_file(
        self,
        filename: str,
        request: Request,
        user: dict = Depends(get_current_user),
    ) -> Response:
        """Proxy file delete request to tools-provider."""
        return await self._proxy_request(request=request, path=f"/api/files/{filename}", method="DELETE", user=user)
