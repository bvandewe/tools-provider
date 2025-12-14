# Scope-Based Access Control

This document describes the scope-based access control architecture for the Tools Provider, enabling fine-grained authorization based on OAuth2 scopes.

## Overview

Scope-based access control complements the existing role-based access control (RBAC) by allowing:

1. **Upstream services** to declare required scopes in their OpenAPI specifications
2. **Administrators** to override or augment scope requirements per source or tool
3. **Tools Provider** to validate user scopes before executing tools
4. **Token Exchange** to request only the scopes needed for a specific operation

This aligns with the core value proposition of **identity propagation with policy enforcement**.

## Design Principles

### 1. Defense in Depth

Scope validation occurs at multiple layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCOPE VALIDATION LAYERS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 1: Keycloak (IdP)                                                   │
│    └─ Issues tokens with scopes based on client configuration              │
│                                                                             │
│  Layer 2: Agent-Host / Client                                              │
│    └─ Requests appropriate scopes during authentication                    │
│                                                                             │
│  Layer 3: Tools Provider (Policy Enforcement Point)                        │
│    └─ Validates user has required scopes BEFORE token exchange             │
│    └─ Requests only required scopes during token exchange                  │
│                                                                             │
│  Layer 4: Upstream Service                                                 │
│    └─ Final validation of scopes in received token                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Fail-Open Default

If no scopes are configured (either via OpenAPI discovery or admin override), the tool executes for any authenticated user. This preserves backward compatibility and respects that **scope enforcement is the upstream's responsibility**.

### 3. Fail-Early Validation

When scopes ARE required, validation happens **before** token exchange to:

- Provide clear error messages to users
- Avoid unnecessary token exchange requests
- Enable policy enforcement at the gateway level

### 4. Least Privilege

Token exchange requests only the scopes required for the specific operation, not the user's full scope set.

## Scope Resolution Hierarchy

Scopes are resolved using a priority hierarchy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SCOPE RESOLUTION HIERARCHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Priority 1: Tool-Level Override (highest)                                 │
│    └─ Stored in ToolDefinition.execution_profile.required_scopes           │
│    └─ Set via admin API or tool configuration                              │
│                                                                             │
│  Priority 2: Source-Level Override                                         │
│    └─ Stored in UpstreamSource.required_scopes                             │
│    └─ Applied to ALL tools from this source                                │
│                                                                             │
│  Priority 3: Auto-Discovered from OpenAPI (lowest)                         │
│    └─ Extracted from operation's security requirement during registration  │
│    └─ Stored in ToolDefinition at discovery time                           │
│                                                                             │
│  If all empty → No scope requirements (fail open)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Resolution Logic

```python
def resolve_required_scopes(
    tool: ToolDefinition,
    source: UpstreamSource,
) -> list[str]:
    """Resolve required scopes for tool execution."""
    # Priority 1: Tool-level override
    if tool.execution_profile.required_scopes:
        return tool.execution_profile.required_scopes

    # Priority 2: Source-level override
    if source.required_scopes:
        return source.required_scopes

    # Priority 3: Auto-discovered (already in tool definition)
    # This would be empty if nothing was discovered
    return []
```

## OpenAPI Scope Discovery

### How Scopes Are Declared

Upstream services declare scopes in their OpenAPI specifications:

```yaml
# Global security scheme with available scopes
components:
  securitySchemes:
    oauth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: "..."
          tokenUrl: "..."
          scopes:
            orders:read: "Read order information"
            orders:write: "Create and modify orders"
            menu:read: "Read menu items"
            menu:admin: "Manage menu items"

# Per-operation scope requirements
paths:
  /orders:
    get:
      security:
        - oauth2: ["orders:read"]
    post:
      security:
        - oauth2: ["orders:write"]

  /menu:
    get:
      security:
        - oauth2: ["menu:read"]
    post:
      security:
        - oauth2: ["menu:admin"]
```

### Extraction Logic

During source registration, the `OpenAPISourceAdapter` extracts scopes:

```python
def _extract_required_scopes(
    self,
    spec: dict[str, Any],
    operation: dict[str, Any],
) -> list[str]:
    """Extract required scopes from operation's security requirement."""
    # Get security requirements (operation-level or spec-level fallback)
    security = operation.get("security", spec.get("security", []))
    if not security:
        return []

    scopes = []
    for requirement in security:
        if isinstance(requirement, dict):
            for scheme_name, scheme_scopes in requirement.items():
                if isinstance(scheme_scopes, list):
                    scopes.extend(scheme_scopes)

    return list(set(scopes))  # Deduplicate
```

## Scope Validation Flow

### Tool Execution with Scope Validation

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     TOOL EXECUTION WITH SCOPE VALIDATION                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Agent calls tool with user's access token                               │
│     └─ Token contains: scope="openid profile orders:read"                   │
│                                                                              │
│  2. Tools Provider resolves required scopes                                 │
│     └─ Tool requires: ["orders:read", "orders:write"]                       │
│                                                                              │
│  3. Scope validation (FAIL EARLY)                                           │
│     ├─ User scopes: ["openid", "profile", "orders:read"]                    │
│     ├─ Required:    ["orders:read", "orders:write"]                         │
│     ├─ Missing:     ["orders:write"]                                        │
│     └─ Result: 403 Forbidden - "Missing required scope: orders:write"       │
│                                                                              │
│  4. If validation passes → Token Exchange                                   │
│     └─ Request token with scope="orders:read orders:write"                  │
│                                                                              │
│  5. Execute tool with exchanged token                                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Validation Implementation

```python
def validate_user_scopes(
    user_scopes: list[str],
    required_scopes: list[str],
) -> tuple[bool, list[str]]:
    """Validate user has all required scopes.

    Args:
        user_scopes: Scopes from user's access token
        required_scopes: Scopes required for the operation

    Returns:
        Tuple of (is_valid, missing_scopes)
    """
    if not required_scopes:
        return True, []

    user_scope_set = set(user_scopes)
    required_scope_set = set(required_scopes)
    missing = required_scope_set - user_scope_set

    return len(missing) == 0, list(missing)
```

## Token Exchange with Scopes

When performing RFC 8693 token exchange, the Tools Provider requests only the scopes needed:

```python
# Before (current implementation)
result = await token_exchanger.exchange_token(
    subject_token=agent_token,
    audience=audience,
    # No scopes specified → Keycloak grants all allowed
)

# After (with scope support)
result = await token_exchanger.exchange_token(
    subject_token=agent_token,
    audience=audience,
    requested_scopes=required_scopes,  # Request only what's needed
)
```

### Keycloak Behavior

When `scope` is included in the token exchange request:

1. Keycloak intersects requested scopes with allowed scopes for the target audience
2. The resulting token contains only the requested (and allowed) scopes
3. If any requested scope is not allowed, the exchange fails with `invalid_scope`

## Data Model Changes

### UpstreamSource Entity

```python
@dataclass
class UpstreamSourceState:
    # ... existing fields ...

    # Scope-based access control
    required_scopes: list[str] = field(default_factory=list)
    """Scopes required for all tools from this source.

    Overrides auto-discovered scopes from OpenAPI.
    Empty list means no source-level scope requirements.
    """
```

### ExecutionProfile Value Object

```python
@dataclass(frozen=True)
class ExecutionProfile:
    # ... existing fields ...

    required_scopes: list[str] = field(default_factory=list)
    """Scopes required to execute this tool.

    Populated from:
    1. Admin override (highest priority)
    2. Source-level requirement
    3. Auto-discovered from OpenAPI security schemes

    Empty list means no scope requirements (fail open).
    """
```

## Error Handling

### Scope Validation Errors

When scope validation fails, return a clear error:

```python
class ScopeValidationError(Exception):
    """Raised when user lacks required scopes."""

    def __init__(
        self,
        message: str,
        required_scopes: list[str],
        missing_scopes: list[str],
        user_scopes: list[str],
    ):
        super().__init__(message)
        self.required_scopes = required_scopes
        self.missing_scopes = missing_scopes
        self.user_scopes = user_scopes
```

### API Response

```json
{
  "error": "insufficient_scope",
  "error_description": "Missing required scope(s): orders:write",
  "required_scopes": ["orders:read", "orders:write"],
  "missing_scopes": ["orders:write"]
}
```

HTTP Status: `403 Forbidden`

## Configuration Examples

### Source with Required Scopes (YAML)

```yaml
# secrets/sources.yaml
sources:
  - name: order-service
    openapi_url: http://order-service:8080/openapi.json
    auth_mode: token_exchange
    default_audience: order-service-backend
    required_scopes:
      - orders:read
      - orders:write
```

### Source Registration API

```json
POST /api/sources
{
  "name": "order-service",
  "openapi_url": "http://order-service:8080/openapi.json",
  "auth_mode": "token_exchange",
  "default_audience": "order-service-backend",
  "required_scopes": ["orders:read", "orders:write"]
}
```

## Keycloak Configuration

### Client Scopes Setup

For scope-based access control to work effectively:

1. **Create custom client scopes** in Keycloak for your upstream services
2. **Assign scopes to clients** as either default or optional
3. **Configure token exchange policies** to allow scope inheritance

```
Realm Settings → Client Scopes → Create:
  - Name: orders:read
  - Type: Optional
  - Protocol: openid-connect
```

### Token Exchange Scope Policy

The `tools-provider-token-exchange` client must be configured to allow scope passthrough:

```
Clients → tools-provider-token-exchange → Client Scopes:
  - Assigned Optional Scopes: orders:read, orders:write, menu:read, etc.
```

## Security Considerations

### 1. Scope Inflation Attack

**Risk:** Malicious client requests more scopes than needed.

**Mitigation:** Tools Provider only requests scopes declared in `required_scopes`, not user-provided scopes.

### 2. Scope Bypass

**Risk:** Attacker modifies tool definition to remove scope requirements.

**Mitigation:**

- Tool definitions are stored in event-sourced aggregate
- Changes are audited via domain events
- Admin role required to modify scope requirements

### 3. Stale Scope Cache

**Risk:** OpenAPI spec changes but cached tools have old scope requirements.

**Mitigation:**

- Source refresh re-parses OpenAPI and updates scope requirements
- Admin can force refresh via API
- Webhook integration for upstream change notification

## Migration Guide

### Existing Sources

Existing sources will continue to work without changes:

1. `required_scopes` defaults to empty list
2. Empty list = fail open (current behavior)
3. No scope validation = backward compatible

### Enabling Scope Validation

To enable scope validation for an existing source:

```bash
# Option 1: Update source via API
PATCH /api/sources/{source_id}
{
  "required_scopes": ["orders:read", "orders:write"]
}

# Option 2: Trigger re-discovery to extract from OpenAPI
POST /api/sources/{source_id}/refresh
```

## Related Documentation

- [Token Exchange Setup](../security/keycloak-token-exchange-setup.md)
- [Upstream Service Integration](../specs/upstream-service-integration-spec.md)
- [Source Registration](../implementation/source-registration.md)
- [Tool Execution](../implementation/tool-execution.md)
