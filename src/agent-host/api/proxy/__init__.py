"""Proxy controllers for forwarding requests to tools-provider.

This package contains controllers that proxy requests from agent-host UI
to the tools-provider backend, enabling access to file upload/download
and other tools-provider endpoints through the same origin.
"""

from api.proxy.api_controller import ApiController

__all__ = [
    "ApiController",
]
