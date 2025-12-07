"""Tool model representing an available tool from the Tools Provider."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolParameter:
    """Represents a parameter for a tool."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[list[Any]] = None

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
        return result


@dataclass
class Tool:
    """
    Represents a tool available from the Tools Provider.

    Tools are fetched from the BFF API and converted to Ollama function format.
    """

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    service_id: Optional[str] = None
    category: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_ollama_function(self) -> dict[str, Any]:
        """
        Convert tool to Ollama function calling format.

        Returns format compatible with Ollama's tools parameter.
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

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
                parameters.append(
                    ToolParameter(
                        name=param_name,
                        type=param_def.get("type", "string"),
                        description=param_def.get("description", ""),
                        required=param_name in required_params,
                        default=param_def.get("default"),
                        enum=param_def.get("enum"),
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
