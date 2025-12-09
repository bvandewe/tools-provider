"""OpenAPI specification fixtures for testing.

Provides mock OpenAPI 3.x specifications for testing the OpenAPISourceAdapter
and related components.
"""

# Simple OpenAPI 3.0 spec with basic operations
SIMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Test API",
        "description": "A simple test API for unit testing",
        "version": "1.0.0",
    },
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "list_users",
                "summary": "List all users",
                "description": "Retrieve a paginated list of users",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10},
                        "description": "Maximum number of results",
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "schema": {"type": "integer", "default": 0},
                        "description": "Number of results to skip",
                    },
                ],
                "responses": {"200": {"description": "Success"}},
            },
            "post": {
                "operationId": "create_user",
                "summary": "Create a new user",
                "description": "Create a new user account",
                "tags": ["users"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "User's full name"},
                                    "email": {"type": "string", "format": "email", "description": "User's email"},
                                },
                                "required": ["name", "email"],
                            }
                        }
                    },
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/users/{user_id}": {
            "get": {
                "operationId": "get_user",
                "summary": "Get a user by ID",
                "description": "Retrieve a single user by their ID",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "The user ID",
                    }
                ],
                "responses": {"200": {"description": "Success"}},
            },
            "put": {
                "operationId": "update_user",
                "summary": "Update a user",
                "description": "Update an existing user",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                },
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "Updated"}},
            },
            "delete": {
                "operationId": "delete_user",
                "summary": "Delete a user",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"204": {"description": "Deleted"}},
            },
        },
    },
}


# OpenAPI spec with $ref references
OPENAPI_SPEC_WITH_REFS = {
    "openapi": "3.0.3",
    "info": {
        "title": "Orders API",
        "version": "2.0.0",
    },
    "servers": [{"url": "https://orders.example.com/api"}],
    "paths": {
        "/orders": {
            "get": {
                "operationId": "list_orders",
                "summary": "List orders",
                "tags": ["orders"],
                "parameters": [
                    {"$ref": "#/components/parameters/PageLimit"},
                    {"$ref": "#/components/parameters/PageOffset"},
                ],
                "responses": {"200": {"description": "Success"}},
            },
            "post": {
                "operationId": "create_order",
                "summary": "Create an order",
                "tags": ["orders"],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateOrder"}}},
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
    },
    "components": {
        "parameters": {
            "PageLimit": {
                "name": "limit",
                "in": "query",
                "schema": {"type": "integer", "maximum": 100, "default": 20},
                "description": "Number of items to return",
            },
            "PageOffset": {
                "name": "offset",
                "in": "query",
                "schema": {"type": "integer", "minimum": 0, "default": 0},
                "description": "Number of items to skip",
            },
        },
        "schemas": {
            "CreateOrder": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "notes": {"type": "string"},
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
}


# OpenAPI spec with OAuth2 security
OPENAPI_SPEC_WITH_SECURITY = {
    "openapi": "3.0.3",
    "info": {
        "title": "Secure API",
        "version": "1.0.0",
    },
    "servers": [{"url": "https://secure.example.com"}],
    "security": [{"oauth2": ["read", "write"]}],
    "paths": {
        "/protected": {
            "get": {
                "operationId": "get_protected",
                "summary": "Get protected resource",
                "tags": ["secure"],
                "responses": {"200": {"description": "Success"}},
            },
        },
    },
    "components": {
        "securitySchemes": {
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "https://auth.example.com/oauth/token",
                        "scopes": {
                            "read": "Read access",
                            "write": "Write access",
                        },
                    }
                },
            },
        },
    },
}


# Minimal OpenAPI spec
MINIMAL_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Minimal", "version": "0.1.0"},
    "paths": {
        "/ping": {
            "get": {
                "summary": "Health check",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
}


# Invalid specs for error testing
INVALID_NO_OPENAPI_VERSION = {
    "info": {"title": "Bad", "version": "1.0"},
    "paths": {},
}

INVALID_SWAGGER_2 = {
    "swagger": "2.0",
    "info": {"title": "Swagger", "version": "1.0"},
    "paths": {},
}

INVALID_NO_PATHS = {
    "openapi": "3.0.0",
    "info": {"title": "No Paths", "version": "1.0"},
}


# YAML format spec (as string for testing)
SIMPLE_OPENAPI_YAML = """
openapi: "3.0.3"
info:
  title: YAML API
  version: "1.0.0"
servers:
  - url: https://yaml.example.com
paths:
  /items:
    get:
      operationId: list_items
      summary: List items
      tags:
        - items
      responses:
        "200":
          description: Success
"""


def get_simple_spec_json() -> str:
    """Get the simple OpenAPI spec as a JSON string."""
    import json

    return json.dumps(SIMPLE_OPENAPI_SPEC)


def get_refs_spec_json() -> str:
    """Get the spec with refs as a JSON string."""
    import json

    return json.dumps(OPENAPI_SPEC_WITH_REFS)


def get_security_spec_json() -> str:
    """Get the spec with security as a JSON string."""
    import json

    return json.dumps(OPENAPI_SPEC_WITH_SECURITY)
