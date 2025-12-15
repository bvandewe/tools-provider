"""Tests for MCP manifest parser.

Tests cover:
- Parsing valid manifest files
- Parsing manifest from JSON strings
- Error handling for invalid manifests
- Package command building
- Environment variable definitions
- Serialization and deserialization
"""

import json
import tempfile
from pathlib import Path

import pytest

from domain.models import (
    McpEnvVarDefinition,
    McpManifest,
    McpManifestError,
    McpPackage,
)

# ============================================================================
# SAMPLE MANIFEST DATA
# ============================================================================


def create_sample_manifest_dict() -> dict:
    """Create a sample manifest dictionary for testing."""
    return {
        "name": "cml-mcp",
        "title": "Cisco Modeling Labs MCP",
        "description": "MCP server for Cisco Modeling Labs network simulation",
        "version": "0.1.0",
        "license": "MIT",
        "repository": {"url": "https://github.com/example/cml-mcp"},
        "iconUrl": "https://example.com/icon.png",
        "packages": [
            {
                "registryType": "pypi",
                "identifier": "cml-mcp",
                "version": "0.1.0",
                "runtimeHint": "uvx",
                "transport": {"type": "stdio"},
                "args": ["--verbose"],
                "environmentVariables": [
                    {
                        "name": "CML_URL",
                        "description": "CML server URL",
                        "isRequired": True,
                        "isSecret": False,
                        "format": "uri",
                    },
                    {
                        "name": "CML_TOKEN",
                        "description": "CML API token",
                        "isRequired": True,
                        "isSecret": True,
                    },
                    {
                        "name": "CML_VERIFY_SSL",
                        "description": "Verify SSL certificates",
                        "isRequired": False,
                        "isSecret": False,
                    },
                ],
            }
        ],
    }


def create_minimal_manifest_dict() -> dict:
    """Create a minimal valid manifest dictionary."""
    return {
        "name": "minimal-mcp",
        "packages": [
            {
                "identifier": "minimal-mcp",
                "transport": {"type": "stdio"},
            }
        ],
    }


def create_multi_package_manifest_dict() -> dict:
    """Create a manifest with multiple packages."""
    return {
        "name": "multi-package-mcp",
        "title": "Multi-Package MCP Server",
        "description": "An MCP server with multiple distribution packages",
        "version": "1.0.0",
        "packages": [
            {
                "registryType": "pypi",
                "identifier": "my-mcp-server",
                "runtimeHint": "uvx",
                "transport": {"type": "stdio"},
            },
            {
                "registryType": "npm",
                "identifier": "@example/my-mcp-server",
                "runtimeHint": "npx",
                "transport": {"type": "stdio"},
            },
            {
                "registryType": "docker",
                "identifier": "example/my-mcp-server:latest",
                "runtimeHint": "docker",
                "transport": {"type": "stdio"},
            },
        ],
    }


# ============================================================================
# MANIFEST PARSING TESTS
# ============================================================================


class TestMcpManifestParsing:
    """Test MCP manifest parsing functionality."""

    def test_parse_from_dict(self) -> None:
        """Test parsing manifest from a dictionary."""
        data = create_sample_manifest_dict()
        manifest = McpManifest.from_dict(data)

        assert manifest.name == "cml-mcp"
        assert manifest.title == "Cisco Modeling Labs MCP"
        assert manifest.description == "MCP server for Cisco Modeling Labs network simulation"
        assert manifest.version == "0.1.0"
        assert manifest.license == "MIT"
        assert manifest.repository_url == "https://github.com/example/cml-mcp"
        assert manifest.icon_url == "https://example.com/icon.png"
        assert len(manifest.packages) == 1

    def test_parse_from_string(self) -> None:
        """Test parsing manifest from a JSON string."""
        data = create_sample_manifest_dict()
        json_str = json.dumps(data)
        manifest = McpManifest.parse_string(json_str)

        assert manifest.name == "cml-mcp"
        assert len(manifest.packages) == 1

    def test_parse_from_file(self) -> None:
        """Test parsing manifest from a file."""
        data = create_sample_manifest_dict()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            manifest = McpManifest.parse(temp_path)
            assert manifest.name == "cml-mcp"
            assert len(manifest.packages) == 1
        finally:
            Path(temp_path).unlink()

    def test_parse_minimal_manifest(self) -> None:
        """Test parsing a minimal manifest with only required fields."""
        data = create_minimal_manifest_dict()
        manifest = McpManifest.from_dict(data)

        assert manifest.name == "minimal-mcp"
        assert manifest.title == "minimal-mcp"  # Defaults to name
        assert manifest.description == ""
        assert manifest.version == "0.0.0"
        assert manifest.repository_url is None
        assert manifest.icon_url is None
        assert manifest.license is None
        assert len(manifest.packages) == 1

    def test_parse_multi_package_manifest(self) -> None:
        """Test parsing manifest with multiple packages."""
        data = create_multi_package_manifest_dict()
        manifest = McpManifest.from_dict(data)

        assert manifest.name == "multi-package-mcp"
        assert len(manifest.packages) == 3

        # Check package registry types
        registry_types = [pkg.registry_type for pkg in manifest.packages]
        assert registry_types == ["pypi", "npm", "docker"]


# ============================================================================
# MANIFEST ERROR HANDLING TESTS
# ============================================================================


class TestMcpManifestErrors:
    """Test MCP manifest error handling."""

    def test_missing_name_raises_error(self) -> None:
        """Test that missing 'name' field raises error."""
        data = {"packages": [{"identifier": "test"}]}

        with pytest.raises(McpManifestError) as exc_info:
            McpManifest.from_dict(data)

        assert "missing required field: 'name'" in str(exc_info.value).lower()

    def test_invalid_json_string_raises_error(self) -> None:
        """Test that invalid JSON raises error."""
        with pytest.raises(McpManifestError) as exc_info:
            McpManifest.parse_string("not valid json {")

        assert "invalid json" in str(exc_info.value).lower()

    def test_file_not_found_raises_error(self) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            McpManifest.parse("/nonexistent/path/server.json")

    def test_no_packages_get_default_raises_error(self) -> None:
        """Test that get_default_package raises error when no packages."""
        data = {"name": "empty-mcp", "packages": []}
        manifest = McpManifest.from_dict(data)

        with pytest.raises(McpManifestError) as exc_info:
            manifest.get_default_package()

        assert "no packages defined" in str(exc_info.value).lower()


# ============================================================================
# PACKAGE TESTS
# ============================================================================


class TestMcpPackage:
    """Test McpPackage functionality."""

    def test_package_parsed_correctly(self) -> None:
        """Test that package fields are parsed correctly."""
        data = create_sample_manifest_dict()
        manifest = McpManifest.from_dict(data)
        package = manifest.get_default_package()

        assert package.registry_type == "pypi"
        assert package.identifier == "cml-mcp"
        assert package.version == "0.1.0"
        assert package.runtime_hint == "uvx"
        assert package.transport_type == "stdio"
        assert package.args == ["--verbose"]
        assert len(package.environment_variables) == 3

    def test_build_command_uvx(self) -> None:
        """Test command building for uvx runtime."""
        package = McpPackage(
            registry_type="pypi",
            identifier="my-mcp-server",
            version="1.0.0",
            runtime_hint="uvx",
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["uvx", "my-mcp-server"]

    def test_build_command_uvx_with_args(self) -> None:
        """Test command building for uvx runtime with arguments."""
        package = McpPackage(
            registry_type="pypi",
            identifier="my-mcp-server",
            version="1.0.0",
            runtime_hint="uvx",
            transport_type="stdio",
            args=["--debug", "--port", "8080"],
        )

        command = package.build_command()
        assert command == ["uvx", "my-mcp-server", "--debug", "--port", "8080"]

    def test_build_command_npx(self) -> None:
        """Test command building for npx runtime."""
        package = McpPackage(
            registry_type="npm",
            identifier="@example/mcp-server",
            version="1.0.0",
            runtime_hint="npx",
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["npx", "-y", "@example/mcp-server"]

    def test_build_command_docker(self) -> None:
        """Test command building for docker runtime."""
        package = McpPackage(
            registry_type="docker",
            identifier="example/mcp-server:latest",
            version="1.0.0",
            runtime_hint="docker",
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["docker", "run", "-i", "--rm", "example/mcp-server:latest"]

    def test_build_command_python(self) -> None:
        """Test command building for python runtime."""
        package = McpPackage(
            registry_type="pypi",
            identifier="my-mcp-server",
            version="1.0.0",
            runtime_hint="python",
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["python", "-m", "my_mcp_server"]

    def test_build_command_node(self) -> None:
        """Test command building for node runtime."""
        package = McpPackage(
            registry_type="npm",
            identifier="./server.js",
            version="1.0.0",
            runtime_hint="node",
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["node", "./server.js"]

    def test_build_command_fallback(self) -> None:
        """Test command building without runtime hint (fallback)."""
        package = McpPackage(
            registry_type="pypi",
            identifier="my-mcp-server",
            version="1.0.0",
            runtime_hint=None,
            transport_type="stdio",
        )

        command = package.build_command()
        assert command == ["my-mcp-server"]


# ============================================================================
# ENVIRONMENT VARIABLE TESTS
# ============================================================================


class TestMcpEnvironmentVariables:
    """Test environment variable parsing and handling."""

    def test_env_vars_parsed_correctly(self) -> None:
        """Test that environment variables are parsed correctly."""
        data = create_sample_manifest_dict()
        manifest = McpManifest.from_dict(data)
        package = manifest.get_default_package()

        env_vars = {env.name: env for env in package.environment_variables}

        assert "CML_URL" in env_vars
        assert env_vars["CML_URL"].is_required is True
        assert env_vars["CML_URL"].is_secret is False
        assert env_vars["CML_URL"].format == "uri"

        assert "CML_TOKEN" in env_vars
        assert env_vars["CML_TOKEN"].is_required is True
        assert env_vars["CML_TOKEN"].is_secret is True

        assert "CML_VERIFY_SSL" in env_vars
        assert env_vars["CML_VERIFY_SSL"].is_required is False

    def test_env_var_defaults(self) -> None:
        """Test environment variable default values."""
        env_var = McpEnvVarDefinition(
            name="TEST_VAR",
            description="",
            is_required=False,
            is_secret=False,
        )

        assert env_var.format == "string"


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================


class TestMcpManifestSerialization:
    """Test manifest serialization and deserialization."""

    def test_round_trip_serialization(self) -> None:
        """Test that manifest can be serialized and deserialized."""
        data = create_sample_manifest_dict()
        manifest = McpManifest.from_dict(data)

        # Serialize
        serialized = manifest.to_dict()

        # Basic fields should match
        assert serialized["name"] == manifest.name
        assert serialized["title"] == manifest.title
        assert serialized["version"] == manifest.version
        assert len(serialized["packages"]) == len(manifest.packages)

    def test_package_serialization(self) -> None:
        """Test package serialization."""
        package = McpPackage(
            registry_type="pypi",
            identifier="test-mcp",
            version="1.0.0",
            runtime_hint="uvx",
            transport_type="stdio",
            args=["--debug"],
            environment_variables=[
                McpEnvVarDefinition(
                    name="TEST_VAR",
                    description="Test variable",
                    is_required=True,
                    is_secret=False,
                )
            ],
        )

        serialized = package.to_dict()

        assert serialized["registry_type"] == "pypi"
        assert serialized["identifier"] == "test-mcp"
        assert serialized["runtime_hint"] == "uvx"
        assert serialized["args"] == ["--debug"]
        assert len(serialized["environment_variables"]) == 1

    def test_compute_hash_consistency(self) -> None:
        """Test that hash computation is consistent."""
        data = create_sample_manifest_dict()
        manifest1 = McpManifest.from_dict(data)
        manifest2 = McpManifest.from_dict(data)

        assert manifest1.compute_hash() == manifest2.compute_hash()

    def test_compute_hash_changes_with_content(self) -> None:
        """Test that hash changes when content changes."""
        data1 = create_sample_manifest_dict()
        data2 = create_sample_manifest_dict()
        data2["version"] = "0.2.0"

        manifest1 = McpManifest.from_dict(data1)
        manifest2 = McpManifest.from_dict(data2)

        assert manifest1.compute_hash() != manifest2.compute_hash()


# ============================================================================
# UTILITY METHOD TESTS
# ============================================================================


class TestMcpManifestUtilities:
    """Test manifest utility methods."""

    def test_get_default_package(self) -> None:
        """Test getting the default package."""
        data = create_multi_package_manifest_dict()
        manifest = McpManifest.from_dict(data)

        default_package = manifest.get_default_package()

        assert default_package.registry_type == "pypi"
        assert default_package.identifier == "my-mcp-server"

    def test_get_package_by_registry_found(self) -> None:
        """Test finding package by registry type."""
        data = create_multi_package_manifest_dict()
        manifest = McpManifest.from_dict(data)

        npm_package = manifest.get_package_by_registry("npm")

        assert npm_package is not None
        assert npm_package.registry_type == "npm"
        assert npm_package.identifier == "@example/my-mcp-server"

    def test_get_package_by_registry_not_found(self) -> None:
        """Test finding package by non-existent registry type."""
        data = create_sample_manifest_dict()
        manifest = McpManifest.from_dict(data)

        cargo_package = manifest.get_package_by_registry("cargo")

        assert cargo_package is None

    def test_get_package_by_registry_case_insensitive(self) -> None:
        """Test that registry lookup is case insensitive."""
        data = create_multi_package_manifest_dict()
        manifest = McpManifest.from_dict(data)

        npm_package = manifest.get_package_by_registry("NPM")

        assert npm_package is not None
        assert npm_package.registry_type == "npm"
