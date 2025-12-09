"""Tool model representing an available tool from the Tools Provider."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    """Represents a parameter for a tool.

    For complex types (arrays, objects), the full_schema field contains
    the complete JSON Schema including nested definitions like 'items'.
    """

    name: str
    type: str
    description: str
    required: bool = True
    default: Any | None = None
    enum: list[Any] | None = None
    items: dict[str, Any] | None = None  # For array types
    properties: dict[str, Any] | None = None  # For object types
    full_schema: dict[str, Any] | None = None  # Complete schema for complex types

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum is not None:
            result["enum"] = self.enum
        if self.items is not None:
            result["items"] = self.items
        if self.properties is not None:
            result["properties"] = self.properties
        return result

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format for LLM tool definitions.

        Returns a complete JSON Schema compatible with OpenAI/Ollama APIs.
        """
        # If we have a full schema stored, use it (preserves all details)
        if self.full_schema:
            schema = dict(self.full_schema)
            # Ensure description is set
            if "description" not in schema and self.description:
                schema["description"] = self.description
            return schema

        # Build schema from individual fields
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }

        if self.enum is not None:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default

        # Handle array types - OpenAI REQUIRES 'items'
        if self.type == "array":
            if self.items is not None:
                schema["items"] = self.items
            else:
                # Default to string items if not specified
                schema["items"] = {"type": "string"}

        # Handle object types
        if self.type == "object":
            if self.properties is not None:
                schema["properties"] = self.properties
            else:
                schema["properties"] = {}

        return schema


@dataclass
class Tool:
    """
    Represents a tool available from the Tools Provider.

    Tools are fetched from the BFF API and converted to Ollama function format.
    """

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    service_id: str | None = None
    category: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_ollama_function(self) -> dict[str, Any]:
        """
        Convert tool to Ollama function calling format.

        Returns format compatible with Ollama's tools parameter.
        Uses to_json_schema() to preserve full schema including 'items' for arrays.
        """
        properties = {}
        required = []

        for param in self.parameters:
            # Use to_json_schema() to get complete schema with items, properties, etc.
            properties[param.name] = param.to_json_schema()

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "service_id": self.service_id,
            "category": self.category,
            "metadata": self.metadata,
        }

    @classmethod
    def from_bff_response(cls, data: dict[str, Any]) -> "Tool":
        """
        Create Tool from Agent API response.

        Expected format from /api/agent/tools endpoint.
        Preserves full schema for complex types (arrays, objects) to ensure
        OpenAI/Ollama API compliance.
        """
        import logging

        logger = logging.getLogger(__name__)

        parameters = []

        # Parse input schema from BFF response (support both snake_case and camelCase)
        input_schema = data.get("input_schema") or data.get("inputSchema", {})
        logger.debug(f"Tool '{data.get('name')}': input_schema type={type(input_schema)}, keys={list(input_schema.keys()) if isinstance(input_schema, dict) else 'N/A'}")

        if isinstance(input_schema, dict):
            props = input_schema.get("properties", {})
            required_params = input_schema.get("required", [])
            logger.debug(f"Tool '{data.get('name')}': found {len(props)} properties, required={required_params}")

            for param_name, param_def in props.items():
                param_type = param_def.get("type", "string")

                # Store full schema for complex types to preserve nested definitions
                full_schema = None
                items = None
                properties = None

                if param_type == "array":
                    # Preserve items schema for arrays (required by OpenAI)
                    items = param_def.get("items")
                    if items is None:
                        # Default to string items if not specified
                        items = {"type": "string"}
                    # Build complete full_schema WITH items (even if original was missing it)
                    full_schema = dict(param_def)  # Copy original
                    full_schema["items"] = items  # Ensure items is present

                elif param_type == "object":
                    # Preserve properties for objects
                    properties = param_def.get("properties")
                    full_schema = param_def

                parameters.append(
                    ToolParameter(
                        name=param_name,
                        type=param_type,
                        description=param_def.get("description", ""),
                        required=param_name in required_params,
                        default=param_def.get("default"),
                        enum=param_def.get("enum"),
                        items=items,
                        properties=properties,
                        full_schema=full_schema,
                    )
                )

        logger.debug(f"Tool '{data.get('name')}' parsed with {len(parameters)} parameters: {[p.name for p in parameters]}")

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=parameters,
            service_id=data.get("source_id") or data.get("serviceId"),
            category=data.get("category"),
            metadata=data.get("metadata", {}),
        )
