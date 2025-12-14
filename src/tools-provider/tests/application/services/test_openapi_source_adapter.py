"""Tests for OpenAPISourceAdapter.

Tests cover:
- Parsing OpenAPI 3.x specifications
- Converting operations to ToolDefinitions
- Handling various parameter types
- Error handling for invalid specs
- URL validation
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from application.services import OpenAPISourceAdapter
from domain.enums import ExecutionMode, SourceType
from tests.fixtures.openapi_specs import (
    INVALID_NO_OPENAPI_VERSION,
    INVALID_NO_PATHS,
    INVALID_SWAGGER_2,
    MINIMAL_OPENAPI_SPEC,
    OPENAPI_SPEC_WITH_REFS,
    SIMPLE_OPENAPI_SPEC,
    SIMPLE_OPENAPI_YAML,
)

# ============================================================================
# ADAPTER BASIC TESTS
# ============================================================================


class TestOpenAPISourceAdapterBasics:
    """Test basic adapter functionality."""

    def test_source_type_is_openapi(self) -> None:
        """Test that adapter reports correct source type."""
        adapter = OpenAPISourceAdapter()
        assert adapter.source_type == SourceType.OPENAPI

    def test_default_timeout(self) -> None:
        """Test default timeout is set."""
        adapter = OpenAPISourceAdapter()
        assert adapter._timeout == 30

    def test_custom_timeout(self) -> None:
        """Test custom timeout is respected."""
        adapter = OpenAPISourceAdapter(timeout_seconds=60)
        assert adapter._timeout == 60


# ============================================================================
# SPEC PARSING TESTS
# ============================================================================


class TestOpenAPISpecParsing:
    """Test OpenAPI specification parsing."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_parse_simple_spec(self, adapter: OpenAPISourceAdapter) -> None:
        """Test parsing a simple OpenAPI spec."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is True
            assert len(result.tools) == 5  # list, create, get, update, delete users
            assert result.source_version == "1.0.0"
            assert result.inventory_hash != ""
            assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_parse_spec_extracts_operation_ids(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that operation IDs are correctly extracted."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            tool_names = [t.name for t in result.tools]
            assert "list_users" in tool_names
            assert "create_user" in tool_names
            assert "get_user" in tool_names
            assert "update_user" in tool_names
            assert "delete_user" in tool_names

    @pytest.mark.asyncio
    async def test_parse_spec_extracts_descriptions(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that descriptions are extracted from summary/description."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_users = next(t for t in result.tools if t.name == "list_users")
            assert "paginated list of users" in list_users.description

    @pytest.mark.asyncio
    async def test_parse_spec_extracts_tags(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that tags are extracted."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_users = next(t for t in result.tools if t.name == "list_users")
            assert "users" in list_users.tags

    @pytest.mark.asyncio
    async def test_parse_yaml_spec(self, adapter: OpenAPISourceAdapter) -> None:
        """Test parsing YAML format spec."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (SIMPLE_OPENAPI_YAML, None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.yaml")

            assert result.success is True
            assert len(result.tools) == 1
            assert result.tools[0].name == "list_items"


# ============================================================================
# INPUT SCHEMA TESTS
# ============================================================================


class TestInputSchemaExtraction:
    """Test JSON Schema extraction for tool inputs."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_query_parameters_in_schema(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that query parameters are included in input schema."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_users = next(t for t in result.tools if t.name == "list_users")
            schema = list_users.input_schema

            assert "limit" in schema["properties"]
            assert "offset" in schema["properties"]
            assert schema["properties"]["limit"]["type"] == "integer"

    @pytest.mark.asyncio
    async def test_path_parameters_in_schema(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that path parameters are included in input schema."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            get_user = next(t for t in result.tools if t.name == "get_user")
            schema = get_user.input_schema

            assert "user_id" in schema["properties"]
            assert "user_id" in schema.get("required", [])

    @pytest.mark.asyncio
    async def test_request_body_in_schema(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that request body properties are included in input schema."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            create_user = next(t for t in result.tools if t.name == "create_user")
            schema = create_user.input_schema

            assert "name" in schema["properties"]
            assert "email" in schema["properties"]
            assert "name" in schema.get("required", [])
            assert "email" in schema.get("required", [])


# ============================================================================
# EXECUTION PROFILE TESTS
# ============================================================================


class TestExecutionProfileGeneration:
    """Test ExecutionProfile generation for tools."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_http_method_is_correct(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that HTTP methods are correctly set."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_users = next(t for t in result.tools if t.name == "list_users")
            create_user = next(t for t in result.tools if t.name == "create_user")
            delete_user = next(t for t in result.tools if t.name == "delete_user")

            assert list_users.execution_profile.method == "GET"
            assert create_user.execution_profile.method == "POST"
            assert delete_user.execution_profile.method == "DELETE"

    @pytest.mark.asyncio
    async def test_url_template_is_correct(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that URL templates are correctly generated.

        URL templates include:
        - Base URL with path parameters (using Jinja2 {{ param }} syntax)
        - Query parameter templating (using Jinja2 conditionals for optional params)
        """
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_users = next(t for t in result.tools if t.name == "list_users")
            get_user = next(t for t in result.tools if t.name == "get_user")

            # list_users has query params (limit, offset), so URL includes query templating
            assert list_users.execution_profile.url_template.startswith("https://api.example.com/v1/users")
            assert "limit" in list_users.execution_profile.url_template
            assert "offset" in list_users.execution_profile.url_template
            # get_user has a path parameter (user_id)
            assert "{{ user_id }}" in get_user.execution_profile.url_template

    @pytest.mark.asyncio
    async def test_execution_mode_is_sync_http(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that all operations default to SYNC_HTTP mode."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            for tool in result.tools:
                assert tool.execution_profile.mode == ExecutionMode.SYNC_HTTP


# ============================================================================
# $REF RESOLUTION TESTS
# ============================================================================


class TestRefResolution:
    """Test $ref resolution in OpenAPI specs."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_parameter_refs_resolved(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that parameter $refs are resolved."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(OPENAPI_SPEC_WITH_REFS), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            list_orders = next(t for t in result.tools if t.name == "list_orders")
            schema = list_orders.input_schema

            assert "limit" in schema["properties"]
            assert "offset" in schema["properties"]

    @pytest.mark.asyncio
    async def test_schema_refs_resolved(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that schema $refs are resolved."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(OPENAPI_SPEC_WITH_REFS), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            create_order = next(t for t in result.tools if t.name == "create_order")
            schema = create_order.input_schema

            assert "product_id" in schema["properties"]
            assert "quantity" in schema["properties"]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test error handling in adapter."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_fetch_error_returns_failure(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that fetch errors return failure result."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", "Connection refused")

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is False
            assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_invalid_json_returns_failure(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that invalid JSON returns failure result."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("{not valid json", None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is False
            assert "Invalid JSON" in result.error

    @pytest.mark.asyncio
    async def test_missing_openapi_version_returns_failure(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that missing openapi version returns failure."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(INVALID_NO_OPENAPI_VERSION), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is False
            assert "openapi" in result.error.lower()

    @pytest.mark.asyncio
    async def test_swagger_2_returns_failure(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that Swagger 2.0 specs return failure."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(INVALID_SWAGGER_2), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is False
            assert "swagger 2.0" in result.error.lower() or "not supported" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_paths_returns_failure(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that missing paths returns failure."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(INVALID_NO_PATHS), None)

            result = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result.success is False
            assert "paths" in result.error.lower()


# ============================================================================
# URL VALIDATION TESTS
# ============================================================================


class TestUrlValidation:
    """Test URL validation functionality."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_valid_url_returns_true(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that valid URLs return True."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(MINIMAL_OPENAPI_SPEC), None)

            result = await adapter.validate_url("https://example.com/openapi.json")

            assert result is True

    @pytest.mark.asyncio
    async def test_invalid_url_returns_false(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that invalid URLs return False."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", "Connection refused")

            result = await adapter.validate_url("https://example.com/openapi.json")

            assert result is False


# ============================================================================
# INVENTORY HASH TESTS
# ============================================================================


class TestInventoryHash:
    """Test inventory hash generation."""

    @pytest.fixture
    def adapter(self) -> OpenAPISourceAdapter:
        """Create adapter instance."""
        return OpenAPISourceAdapter()

    @pytest.mark.asyncio
    async def test_same_spec_produces_same_hash(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that identical specs produce identical hashes."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)

            result1 = await adapter.fetch_and_normalize("https://example.com/openapi.json")
            result2 = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result1.inventory_hash == result2.inventory_hash

    @pytest.mark.asyncio
    async def test_different_specs_produce_different_hashes(self, adapter: OpenAPISourceAdapter) -> None:
        """Test that different specs produce different hashes."""
        with patch.object(adapter, "_fetch_spec", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (json.dumps(SIMPLE_OPENAPI_SPEC), None)
            result1 = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            mock_fetch.return_value = (json.dumps(MINIMAL_OPENAPI_SPEC), None)
            result2 = await adapter.fetch_and_normalize("https://example.com/openapi.json")

            assert result1.inventory_hash != result2.inventory_hash
