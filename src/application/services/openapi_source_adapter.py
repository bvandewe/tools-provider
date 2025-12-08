"""OpenAPI Source Adapter for parsing OpenAPI 3.x specifications.

This adapter fetches OpenAPI 3.x specifications from URLs and converts
each operation into a normalized ToolDefinition that can be used by AI agents.

Supports:
- OpenAPI 3.0.x and 3.1.x specifications
- JSON and YAML formats
- Bearer token, API key, and OAuth2 authentication
- Path parameters, query parameters, and request bodies
- JSON Schema extraction for tool input schemas
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
import yaml

from domain.enums import ExecutionMode, SourceType
from domain.models import AuthConfig, ExecutionProfile, ToolDefinition

from .source_adapter import IngestionResult, SourceAdapter

logger = logging.getLogger(__name__)

# HTTP methods that typically have request bodies
METHODS_WITH_BODY = {"post", "put", "patch"}

# HTTP methods to expose as tools (HEAD and OPTIONS typically not useful for agents)
SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}


class OpenAPISourceAdapter(SourceAdapter):
    """Adapter for parsing OpenAPI 3.x specifications into ToolDefinitions.

    This adapter:
    1. Fetches OpenAPI specs from URLs (JSON or YAML)
    2. Parses the specification and extracts operations
    3. Converts each operation to a ToolDefinition with proper input schema
    4. Generates ExecutionProfiles for invoking the operations

    The resulting ToolDefinitions can be used by AI agents to discover
    and invoke API endpoints.
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        default_audience: str = "",
    ):
        """Initialize the OpenAPI adapter.

        Args:
            timeout_seconds: Default timeout for HTTP requests
            default_audience: Default audience for token exchange
        """
        self._timeout = timeout_seconds
        self._default_audience = default_audience

    @property
    def source_type(self) -> SourceType:
        """Return the type of source this adapter handles."""
        return SourceType.OPENAPI

    async def fetch_and_normalize(
        self,
        url: str,
        auth_config: Optional[AuthConfig] = None,
    ) -> IngestionResult:
        """Fetch an OpenAPI spec and convert it to ToolDefinitions.

        Args:
            url: URL to the OpenAPI specification (JSON or YAML)
            auth_config: Optional authentication for fetching the spec

        Returns:
            IngestionResult with parsed tools or error information
        """
        logger.info(f"Fetching OpenAPI spec from: {url}")
        warnings: List[str] = []

        try:
            # Fetch the specification
            spec_content, fetch_error = await self._fetch_spec(url, auth_config)
            if fetch_error:
                return IngestionResult.failure(fetch_error)

            # Parse the specification (JSON or YAML)
            spec, parse_error = self._parse_spec(spec_content, url)
            if parse_error:
                return IngestionResult.failure(parse_error)

            # Validate it's an OpenAPI spec
            validation_error = self._validate_openapi_spec(spec)
            if validation_error:
                return IngestionResult.failure(validation_error)

            # Extract base URL from spec
            base_url = self._extract_base_url(spec, url)

            # Extract version for metadata
            source_version = spec.get("info", {}).get("version")

            # Parse all operations into ToolDefinitions
            tools: List[ToolDefinition] = []
            paths = spec.get("paths", {})

            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue

                for method, operation in path_item.items():
                    # Skip non-operation fields (parameters, servers, etc.)
                    if method.lower() not in SUPPORTED_METHODS:
                        continue

                    if not isinstance(operation, dict):
                        continue

                    try:
                        tool = self._parse_operation(
                            spec=spec,
                            path=path,
                            method=method.upper(),
                            operation=operation,
                            base_url=base_url,
                        )
                        if tool:
                            tools.append(tool)
                    except Exception as e:
                        warning = f"Failed to parse operation {method.upper()} {path}: {str(e)}"
                        logger.warning(warning)
                        warnings.append(warning)

            if not tools:
                return IngestionResult.failure("No valid operations found in OpenAPI spec")

            # Compute inventory hash
            inventory_hash = self._compute_inventory_hash(tools)

            logger.info(f"Successfully parsed {len(tools)} tools from OpenAPI spec")

            return IngestionResult(
                tools=tools,
                inventory_hash=inventory_hash,
                success=True,
                source_version=source_version,
                warnings=warnings,
            )

        except Exception as e:
            logger.exception(f"Unexpected error parsing OpenAPI spec: {e}")
            return IngestionResult.failure(f"Unexpected error: {str(e)}")

    async def validate_url(self, url: str, auth_config: Optional[AuthConfig] = None) -> bool:
        """Validate that a URL points to a valid OpenAPI specification.

        Args:
            url: URL to validate
            auth_config: Optional authentication configuration

        Returns:
            True if URL points to valid OpenAPI spec
        """
        try:
            spec_content, error = await self._fetch_spec(url, auth_config)
            if error:
                return False

            spec, error = self._parse_spec(spec_content, url)
            if error:
                return False

            validation_error = self._validate_openapi_spec(spec)
            return validation_error is None

        except Exception:
            return False

    # =========================================================================
    # Private Methods - Fetching
    # =========================================================================

    async def _fetch_spec(
        self,
        url: str,
        auth_config: Optional[AuthConfig] = None,
    ) -> Tuple[str, Optional[str]]:
        """Fetch the OpenAPI specification from a URL.

        Args:
            url: URL to fetch
            auth_config: Optional authentication

        Returns:
            Tuple of (content, error_message). Error is None on success.
        """
        headers = self._build_auth_headers(auth_config)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)

                if response.status_code == 401:
                    return "", "Authentication required but credentials invalid or missing"
                elif response.status_code == 403:
                    return "", "Access forbidden - insufficient permissions"
                elif response.status_code == 404:
                    return "", "OpenAPI specification not found at URL"
                elif response.status_code >= 400:
                    return "", f"HTTP error {response.status_code}: {response.reason_phrase}"

                return response.text, None

        except httpx.TimeoutException:
            return "", f"Request timed out after {self._timeout} seconds"
        except httpx.ConnectError:
            return "", f"Failed to connect to {urlparse(url).netloc}"
        except Exception as e:
            return "", f"Failed to fetch specification: {str(e)}"

    def _build_auth_headers(self, auth_config: Optional[AuthConfig]) -> Dict[str, str]:
        """Build HTTP headers for authentication.

        Args:
            auth_config: Authentication configuration

        Returns:
            Dictionary of headers to include in request
        """
        headers: Dict[str, str] = {
            "Accept": "application/json, application/yaml, text/yaml, */*",
            "User-Agent": "MCP-Tools-Provider/1.0",
        }

        if auth_config is None or auth_config.auth_type == "none":
            return headers

        if auth_config.auth_type == "bearer" and auth_config.bearer_token:
            headers["Authorization"] = f"Bearer {auth_config.bearer_token}"
        elif auth_config.auth_type == "api_key":
            if auth_config.api_key_in == "header" and auth_config.api_key_name:  # pragma: allowlist secret
                headers[auth_config.api_key_name] = auth_config.api_key_value or ""

        return headers

    # =========================================================================
    # Private Methods - Parsing
    # =========================================================================

    def _parse_spec(self, content: str, url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse the specification content as JSON or YAML.

        Args:
            content: Raw specification content
            url: Original URL (used for format hints)

        Returns:
            Tuple of (parsed_spec, error_message). Error is None on success.
        """
        content = content.strip()

        # Try JSON first (most common)
        if content.startswith("{"):
            try:
                return json.loads(content), None
            except json.JSONDecodeError as e:
                return None, f"Invalid JSON: {str(e)}"

        # Try YAML
        try:
            spec = yaml.safe_load(content)
            if isinstance(spec, dict):
                return spec, None
            return None, "YAML content is not a valid OpenAPI document"
        except yaml.YAMLError as e:
            return None, f"Invalid YAML: {str(e)}"

    def _validate_openapi_spec(self, spec: Dict[str, Any]) -> Optional[str]:
        """Validate that the spec is a valid OpenAPI 3.x document.

        Args:
            spec: Parsed specification

        Returns:
            Error message if invalid, None if valid
        """
        # Check for OpenAPI version
        openapi_version = spec.get("openapi")
        if not openapi_version:
            # Could be Swagger 2.0
            swagger_version = spec.get("swagger")
            if swagger_version:
                return "Swagger 2.0 is not supported. Please upgrade to OpenAPI 3.x"
            return "Missing 'openapi' field - not a valid OpenAPI specification"

        # Validate version is 3.x
        if not str(openapi_version).startswith("3."):
            return f"OpenAPI version {openapi_version} is not supported. Only 3.x is supported."

        # Check for required fields
        if "info" not in spec:
            return "Missing 'info' field in OpenAPI specification"

        if "paths" not in spec:
            return "Missing 'paths' field in OpenAPI specification"

        return None

    def _extract_base_url(self, spec: Dict[str, Any], spec_url: str) -> str:
        """Extract the base URL for API calls from the spec.

        Tries servers array first, falls back to spec URL host.

        Args:
            spec: Parsed OpenAPI specification
            spec_url: URL where the spec was fetched from

        Returns:
            Base URL for API calls
        """
        servers = spec.get("servers", [])
        if servers and isinstance(servers, list) and servers[0].get("url"):
            server_url = servers[0]["url"]
            # Handle relative URLs
            if server_url.startswith("/"):
                parsed = urlparse(spec_url)
                return f"{parsed.scheme}://{parsed.netloc}{server_url}"
            return server_url

        # Fall back to spec URL's host
        parsed = urlparse(spec_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    # =========================================================================
    # Private Methods - Operation Parsing
    # =========================================================================

    def _parse_operation(
        self,
        spec: Dict[str, Any],
        path: str,
        method: str,
        operation: Dict[str, Any],
        base_url: str,
    ) -> Optional[ToolDefinition]:
        """Parse a single OpenAPI operation into a ToolDefinition.

        Args:
            spec: Full OpenAPI spec (for resolving $ref)
            path: API path (e.g., "/users/{id}")
            method: HTTP method (e.g., "GET")
            operation: Operation object from spec
            base_url: Base URL for the API

        Returns:
            ToolDefinition or None if operation should be skipped
        """
        # Generate operation ID (tool name)
        operation_id = operation.get("operationId")
        if not operation_id:
            # Generate from method + path
            operation_id = self._generate_operation_id(method, path)

        # Extract description
        description = operation.get("description") or operation.get("summary") or f"{method} {path}"

        # Build input schema from parameters and request body
        input_schema = self._build_input_schema(spec, path, method, operation)

        # Extract tags
        tags = operation.get("tags", [])

        # Build URL template
        url_template = self._build_url_template(base_url, path)

        # Build body template if needed
        body_template = None
        if method.lower() in METHODS_WITH_BODY:
            body_template = self._build_body_template(spec, operation)

        # Determine content type
        content_type = self._get_request_content_type(operation)

        # Extract security requirements for audience
        required_audience = self._extract_required_audience(spec, operation)

        # Build execution profile
        execution_profile = ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method=method,
            url_template=url_template,
            headers_template={},
            body_template=body_template,
            content_type=content_type,
            required_audience=required_audience or self._default_audience,
            required_scopes=[],  # Could extract from security schemes
            timeout_seconds=self._timeout,
        )

        return ToolDefinition(
            name=operation_id,
            description=description,
            input_schema=input_schema,
            execution_profile=execution_profile,
            source_path=path,
            tags=tags,
            deprecated=operation.get("deprecated", False),
        )

    def _generate_operation_id(self, method: str, path: str) -> str:
        """Generate an operation ID from method and path.

        Args:
            method: HTTP method
            path: API path

        Returns:
            Generated operation ID (e.g., "get_users_by_id")
        """
        # Convert path to snake_case identifier
        path_parts = path.strip("/").replace("{", "").replace("}", "").split("/")
        path_id = "_".join(part for part in path_parts if part)

        return f"{method.lower()}_{path_id}" if path_id else method.lower()

    def _build_url_template(self, base_url: str, path: str) -> str:
        """Build a Jinja2 URL template from base URL and path.

        Converts OpenAPI path params {id} to Jinja2 {{ id }}.

        Args:
            base_url: API base URL
            path: API path with parameters

        Returns:
            URL template with Jinja2 placeholders
        """
        import re

        # Convert {param} to {{ param }}
        template_path = re.sub(r"\{(\w+)\}", r"{{ \1 }}", path)

        # Ensure base URL doesn't end with /
        base_url = base_url.rstrip("/")

        return f"{base_url}{template_path}"

    def _build_input_schema(
        self,
        spec: Dict[str, Any],
        path: str,
        method: str,
        operation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a JSON Schema for the tool's input parameters.

        Combines path parameters, query parameters, and request body schema.

        Args:
            spec: Full OpenAPI spec (for resolving $ref)
            path: API path
            method: HTTP method
            operation: Operation object

        Returns:
            JSON Schema for tool input
        """
        properties: Dict[str, Any] = {}
        required: List[str] = []

        # Process parameters (path, query, header)
        parameters = operation.get("parameters", [])
        for param in parameters:
            param = self._resolve_ref(spec, param)
            if not isinstance(param, dict):
                continue

            param_name = param.get("name")
            param_in = param.get("in")

            # Skip header parameters (handled separately)
            if param_in == "header":
                continue

            if param_name:
                param_schema = param.get("schema", {})
                param_schema = self._resolve_ref(spec, param_schema)

                properties[param_name] = {
                    "type": param_schema.get("type", "string"),
                    "description": param.get("description", f"Parameter: {param_name}"),
                }

                # Copy additional schema fields
                for field in ["enum", "default", "minimum", "maximum", "pattern", "format"]:
                    if field in param_schema:
                        properties[param_name][field] = param_schema[field]

                if param.get("required", False):
                    required.append(param_name)

        # Process request body for POST/PUT/PATCH
        if method.lower() in METHODS_WITH_BODY:
            request_body = operation.get("requestBody", {})
            request_body = self._resolve_ref(spec, request_body)

            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})
                schema = self._resolve_ref(spec, schema)

                if isinstance(schema, dict):
                    # Merge body schema properties
                    body_props = schema.get("properties", {})
                    for prop_name, prop_schema in body_props.items():
                        prop_schema = self._resolve_ref(spec, prop_schema)
                        properties[prop_name] = self._simplify_schema(prop_schema)

                    # Add required fields from body
                    body_required = schema.get("required", [])
                    required.extend(body_required)

                    if request_body.get("required", False) and body_required:
                        pass  # Already added above

        # Build final schema
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema["required"] = list(set(required))  # Deduplicate

        return schema

    def _simplify_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify a JSON Schema for tool input display.

        Removes complex nested structures while preserving essential info.

        Args:
            schema: Original JSON Schema

        Returns:
            Simplified schema
        """
        if not isinstance(schema, dict):
            return {"type": "string"}

        simplified: Dict[str, Any] = {}

        # Copy basic fields
        for field in ["type", "description", "enum", "default", "format", "minimum", "maximum", "pattern"]:
            if field in schema:
                simplified[field] = schema[field]

        # Set default type if missing
        if "type" not in simplified:
            simplified["type"] = "string"

        return simplified

    def _build_body_template(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
    ) -> Optional[str]:
        """Build a Jinja2 template for the request body.

        Args:
            spec: Full OpenAPI spec
            operation: Operation object

        Returns:
            Jinja2 template string or None
        """
        request_body = operation.get("requestBody", {})
        request_body = self._resolve_ref(spec, request_body)

        if not isinstance(request_body, dict):
            return None

        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        schema = self._resolve_ref(spec, schema)

        if not isinstance(schema, dict):
            return None

        properties = schema.get("properties", {})
        if not properties:
            return None

        # Build a template that includes all properties as Jinja2 variables
        # This creates: {"prop1": {{ prop1 | tojson }}, "prop2": {{ prop2 | tojson }}}
        parts = []
        for prop_name in properties.keys():
            parts.append(f'"{prop_name}": {{{{ {prop_name} | tojson }}}}')

        return "{" + ", ".join(parts) + "}"

    def _get_request_content_type(self, operation: Dict[str, Any]) -> str:
        """Get the content type for the request body.

        Args:
            operation: Operation object

        Returns:
            Content type string
        """
        request_body = operation.get("requestBody", {})
        if isinstance(request_body, dict):
            content = request_body.get("content", {})
            if "application/json" in content:
                return "application/json"
            if "application/x-www-form-urlencoded" in content:
                return "application/x-www-form-urlencoded"
            if "multipart/form-data" in content:
                return "multipart/form-data"
            # Return first content type if any
            if content:
                return next(iter(content.keys()))

        return "application/json"

    def _extract_required_audience(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
    ) -> Optional[str]:
        """Extract the required audience for token exchange.

        Looks at security schemes to determine the target audience.

        Args:
            spec: Full OpenAPI spec
            operation: Operation object

        Returns:
            Audience string or None
        """
        # Get security requirements (operation-level or spec-level)
        security = operation.get("security", spec.get("security", []))
        if not security:
            return None

        # Look up security schemes
        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        for requirement in security:
            if isinstance(requirement, dict):
                for scheme_name in requirement.keys():
                    scheme = security_schemes.get(scheme_name, {})
                    if scheme.get("type") == "oauth2":
                        # Check for x-audience extension first (explicit audience)
                        flows = scheme.get("flows", {})
                        for flow in flows.values():
                            if isinstance(flow, dict):
                                # Look for explicit audience in extension
                                if "x-audience" in flow:
                                    return flow["x-audience"]
                        # Don't use scheme_name as audience - it's not a valid Keycloak client
                        # Return None to use the agent's token directly
                        return None

        return None

    def _resolve_ref(self, spec: Dict[str, Any], obj: Any) -> Any:
        """Resolve a $ref reference in the OpenAPI spec.

        Args:
            spec: Full OpenAPI specification
            obj: Object that may contain a $ref

        Returns:
            Resolved object or original if no $ref
        """
        if not isinstance(obj, dict) or "$ref" not in obj:
            return obj

        ref_path = obj["$ref"]
        if not ref_path.startswith("#/"):
            # External refs not supported
            return obj

        # Navigate to referenced object
        parts = ref_path[2:].split("/")
        current = spec
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, {})
            else:
                return obj

        return current if current else obj

    # =========================================================================
    # Private Methods - Hashing
    # =========================================================================

    def _compute_inventory_hash(self, tools: List[ToolDefinition]) -> str:
        """Compute a hash of the entire tool inventory for change detection.

        Args:
            tools: List of parsed tools

        Returns:
            SHA-256 hash (first 16 chars) of the inventory
        """
        # Sort tools by name for deterministic hashing
        sorted_tools = sorted(tools, key=lambda t: t.name)

        # Create content string
        content_parts = []
        for tool in sorted_tools:
            content_parts.append(json.dumps(tool.to_dict(), sort_keys=True))

        content = "\n".join(content_parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
