"""MCP Environment Variable Resolver.

Resolves environment variables required by MCP plugins from various sources:
- Static configuration (from source registration)
- File-based secrets (sources.yaml)
- OS environment variables
- User-provided runtime values
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from domain.models import McpSourceConfig

logger = logging.getLogger(__name__)

# Default path for MCP plugin secrets
DEFAULT_MCP_SECRETS_PATH = "secrets/mcp-plugins.yaml"  # pragma: allowlist secret


@dataclass
class ResolutionResult:
    """Result of environment variable resolution.

    Attributes:
        resolved: Dictionary of successfully resolved variables
        missing: List of required variables that could not be resolved
        warnings: List of warning messages during resolution
    """

    resolved: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if all required variables were resolved."""
        return len(self.missing) == 0


class McpEnvironmentResolver:
    """Resolver for MCP plugin environment variables.

    Resolves environment variables from multiple sources in priority order:
    1. Runtime overrides (passed at execution time)
    2. Source-specific secrets (from mcp-plugins.yaml)
    3. Config values (stored with the source registration)
    4. OS environment variables (fallback)

    The resolver supports secret masking in logs and tracks which
    required variables could not be resolved.

    Usage:
        resolver = McpEnvironmentResolver()
        result = resolver.resolve(config, runtime_overrides={"API_KEY": "value"})

        if not result.is_complete:
            raise ValueError(f"Missing required env vars: {result.missing}")

        # Use resolved environment
        environment = result.resolved
    """

    def __init__(
        self,
        secrets_path: str | Path | None = None,
        allow_os_env: bool = True,
    ):
        """Initialize the environment resolver.

        Args:
            secrets_path: Path to the MCP secrets YAML file.
                         Defaults to secrets/mcp-plugins.yaml.
                         Can also be set via MCP_SECRETS_PATH env var.
            allow_os_env: Whether to fall back to OS environment variables.
        """
        self._secrets: dict[str, dict[str, str]] = {}
        self._allow_os_env = allow_os_env
        self._path: Path | None = None

        # Resolve path: explicit > env var > default
        if secrets_path:
            self._path = Path(secrets_path)
        elif os.environ.get("MCP_SECRETS_PATH"):
            self._path = Path(os.environ["MCP_SECRETS_PATH"])
        else:
            self._path = Path(DEFAULT_MCP_SECRETS_PATH)

        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from YAML file.

        Expected format:
        ```yaml
        plugins:
          cml-mcp:
            CML_URL: https://cml.example.com
            CML_TOKEN: secret-token
          another-plugin:
            API_KEY: another-key
        ```
        """
        if not self._path or not self._path.exists():
            logger.debug(f"MCP secrets file not found: {self._path}")
            return

        try:
            with open(self._path) as f:
                data = yaml.safe_load(f)

            if data and isinstance(data.get("plugins"), dict):
                self._secrets = data["plugins"]
                logger.info(f"Loaded MCP secrets for {len(self._secrets)} plugin(s)")
            else:
                logger.debug(f"MCP secrets file {self._path} has no 'plugins' section")

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse MCP secrets file {self._path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load MCP secrets file {self._path}: {e}")

    def resolve(
        self,
        config: "McpSourceConfig",
        runtime_overrides: dict[str, str] | None = None,
        plugin_key: str | None = None,
    ) -> ResolutionResult:
        """Resolve environment variables for an MCP plugin.

        Resolution order (highest priority first):
        1. Runtime overrides
        2. Plugin-specific secrets from file
        3. Config.environment (stored with source)
        4. OS environment (if allow_os_env=True)

        Args:
            config: MCP source configuration with env_definitions
            runtime_overrides: Optional dict of values to use first
            plugin_key: Key to look up in secrets file.
                       Defaults to plugin name from manifest path.

        Returns:
            ResolutionResult with resolved values and any missing required vars
        """
        result = ResolutionResult()
        overrides = runtime_overrides or {}

        # Determine plugin key for secrets lookup
        if not plugin_key:
            # Extract plugin name from manifest path or plugin_dir
            plugin_key = Path(config.plugin_dir).name

        # Get plugin-specific secrets
        plugin_secrets = self._secrets.get(plugin_key, {})

        for env_def in config.env_definitions:
            var_name = env_def.name
            resolved_value: str | None = None
            source: str = ""

            # Try resolution in priority order
            if var_name in overrides:
                resolved_value = overrides[var_name]
                source = "runtime"
            elif var_name in plugin_secrets:
                resolved_value = plugin_secrets[var_name]
                source = "secrets"
            elif var_name in config.environment:
                resolved_value = config.environment[var_name]
                source = "config"
            elif self._allow_os_env and var_name in os.environ:
                resolved_value = os.environ[var_name]
                source = "os_env"

            if resolved_value is not None:
                result.resolved[var_name] = resolved_value
                # Log resolution (mask secrets)
                display_value = "***" if env_def.is_secret else resolved_value[:20] + "..." if len(resolved_value) > 20 else resolved_value
                logger.debug(f"Resolved {var_name}={display_value} (from {source})")
            elif env_def.is_required:
                result.missing.append(var_name)
                result.warnings.append(f"Required environment variable '{var_name}' is not set")
            else:
                # Optional var not found - that's okay
                logger.debug(f"Optional env var '{var_name}' not set")

        return result

    def resolve_to_dict(
        self,
        config: "McpSourceConfig",
        runtime_overrides: dict[str, str] | None = None,
        plugin_key: str | None = None,
    ) -> dict[str, str]:
        """Convenience method to resolve and return just the environment dict.

        Raises ValueError if any required variables are missing.

        Args:
            config: MCP source configuration
            runtime_overrides: Optional runtime values
            plugin_key: Key for secrets lookup

        Returns:
            Dictionary of resolved environment variables

        Raises:
            ValueError: If required variables are missing
        """
        result = self.resolve(config, runtime_overrides, plugin_key)

        if not result.is_complete:
            raise ValueError(f"Missing required MCP environment variables: {result.missing}")

        return result.resolved

    def get_plugin_secrets(self, plugin_key: str) -> dict[str, str]:
        """Get secrets for a specific plugin.

        Args:
            plugin_key: Plugin identifier in the secrets file

        Returns:
            Dictionary of secrets for the plugin, or empty dict
        """
        return dict(self._secrets.get(plugin_key, {}))

    def has_plugin_secrets(self, plugin_key: str) -> bool:
        """Check if secrets exist for a plugin.

        Args:
            plugin_key: Plugin identifier to check

        Returns:
            True if secrets are configured for this plugin
        """
        return plugin_key in self._secrets

    @property
    def loaded_plugins(self) -> list[str]:
        """Get list of plugins that have secrets configured."""
        return list(self._secrets.keys())

    def reload(self) -> None:
        """Reload secrets from the file.

        Useful for development or if secrets are updated.
        """
        self._secrets.clear()
        self._load_secrets()

    def validate_config(self, config: "McpSourceConfig") -> list[str]:
        """Validate that all required environment variables can be resolved.

        Does not actually resolve values, just checks availability.

        Args:
            config: MCP source configuration to validate

        Returns:
            List of required variable names that cannot be resolved
        """
        missing = []
        plugin_key = Path(config.plugin_dir).name
        plugin_secrets = self._secrets.get(plugin_key, {})

        for env_def in config.env_definitions:
            if not env_def.is_required:
                continue

            var_name = env_def.name
            has_value = var_name in config.environment or var_name in plugin_secrets or (self._allow_os_env and var_name in os.environ)

            if not has_value:
                missing.append(var_name)

        return missing
