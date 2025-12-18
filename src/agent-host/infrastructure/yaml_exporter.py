"""YAML Exporter for seed-compatible export.

This module provides utilities to export AgentDefinitions and
ConversationTemplates to YAML format that is compatible with the
DatabaseSeeder for re-importing.

Used by the Admin UI export functionality.
"""

import logging
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from integration.models.definition_dto import AgentDefinitionDto
from integration.models.template_dto import ConversationTemplateDto

logger = logging.getLogger(__name__)


class YamlExporter:
    """Service for exporting entities to seed-compatible YAML.

    Exports AgentDefinitions and ConversationTemplates to YAML format
    that can be used with DatabaseSeeder for re-importing.
    """

    # Fields to exclude from export (internal/audit fields)
    DEFINITION_EXCLUDE_FIELDS = {"created_at", "updated_at", "version"}
    TEMPLATE_EXCLUDE_FIELDS = {"created_at", "updated_at", "version"}

    def __init__(self, include_audit_fields: bool = False) -> None:
        """Initialize the YAML exporter.

        Args:
            include_audit_fields: If True, include created_at/updated_at/version
        """
        self._include_audit_fields = include_audit_fields

    def export_definition(self, definition: AgentDefinitionDto) -> str:
        """Export an AgentDefinition to YAML string.

        Args:
            definition: The AgentDefinitionDto to export

        Returns:
            YAML string representation
        """
        data = self._definition_to_export_dict(definition)
        return self._to_yaml_string(data)

    def export_template(self, template: ConversationTemplateDto) -> str:
        """Export a ConversationTemplate to YAML string.

        Args:
            template: The ConversationTemplateDto to export

        Returns:
            YAML string representation
        """
        data = self._template_to_export_dict(template)
        return self._to_yaml_string(data)

    def export_definition_to_file(self, definition: AgentDefinitionDto, output_path: str | Path) -> None:
        """Export an AgentDefinition to a YAML file.

        Args:
            definition: The AgentDefinitionDto to export
            output_path: Path to write the YAML file
        """
        yaml_content = self.export_definition(definition)
        Path(output_path).write_text(yaml_content, encoding="utf-8")
        logger.info(f"Exported definition '{definition.id}' to {output_path}")

    def export_template_to_file(self, template: ConversationTemplateDto, output_path: str | Path) -> None:
        """Export a ConversationTemplate to a YAML file.

        Args:
            template: The ConversationTemplateDto to export
            output_path: Path to write the YAML file
        """
        yaml_content = self.export_template(template)
        Path(output_path).write_text(yaml_content, encoding="utf-8")
        logger.info(f"Exported template '{template.id}' to {output_path}")

    def _definition_to_export_dict(self, definition: AgentDefinitionDto) -> dict[str, Any]:
        """Convert AgentDefinitionDto to export dictionary.

        Args:
            definition: The AgentDefinitionDto to convert

        Returns:
            Dictionary suitable for YAML export
        """
        data = definition.to_dict()

        # Remove excluded fields
        if not self._include_audit_fields:
            for field in self.DEFINITION_EXCLUDE_FIELDS:
                data.pop(field, None)

        # Clean up None values for cleaner YAML
        data = self._clean_none_values(data)

        return data

    def _template_to_export_dict(self, template: ConversationTemplateDto) -> dict[str, Any]:
        """Convert ConversationTemplateDto to export dictionary.

        Args:
            template: The ConversationTemplateDto to convert

        Returns:
            Dictionary suitable for YAML export
        """
        data = template.to_dict()

        # Remove excluded fields
        if not self._include_audit_fields:
            for field in self.TEMPLATE_EXCLUDE_FIELDS:
                data.pop(field, None)

        # Clean up None values for cleaner YAML
        data = self._clean_none_values(data)

        return data

    def _clean_none_values(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove None values from dictionary recursively.

        Args:
            data: Dictionary to clean

        Returns:
            Cleaned dictionary
        """
        result = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                cleaned = self._clean_none_values(value)
                if cleaned:  # Only include non-empty dicts
                    result[key] = cleaned
            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = self._clean_none_values(item)
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    elif item is not None:
                        cleaned_list.append(item)
                if cleaned_list:
                    result[key] = cleaned_list
            else:
                result[key] = value
        return result

    def _to_yaml_string(self, data: dict[str, Any]) -> str:
        """Convert dictionary to YAML string with nice formatting.

        Args:
            data: Dictionary to convert

        Returns:
            Formatted YAML string
        """

        # Custom representer for multiline strings
        def str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
            if "\n" in data:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        # Custom representer for datetime
        def datetime_representer(dumper: yaml.SafeDumper, data: datetime) -> yaml.ScalarNode:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data.isoformat())

        # Create custom dumper
        class CustomDumper(yaml.SafeDumper):
            pass

        CustomDumper.add_representer(str, str_representer)
        CustomDumper.add_representer(datetime, datetime_representer)

        output = StringIO()
        yaml.dump(
            data,
            output,
            Dumper=CustomDumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        return output.getvalue()


# =============================================================================
# Convenience Functions
# =============================================================================


def export_definition_to_yaml(definition: AgentDefinitionDto, include_audit: bool = False) -> str:
    """Export an AgentDefinitionDto to YAML string.

    Args:
        definition: The AgentDefinitionDto to export
        include_audit: Include audit fields (created_at, etc.)

    Returns:
        YAML string
    """
    exporter = YamlExporter(include_audit_fields=include_audit)
    return exporter.export_definition(definition)


def export_template_to_yaml(template: ConversationTemplateDto, include_audit: bool = False) -> str:
    """Export a ConversationTemplateDto to YAML string.

    Args:
        template: The ConversationTemplateDto to export
        include_audit: Include audit fields (created_at, etc.)

    Returns:
        YAML string
    """
    exporter = YamlExporter(include_audit_fields=include_audit)
    return exporter.export_template(template)
