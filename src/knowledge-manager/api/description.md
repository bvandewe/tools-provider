# Knowledge Manager API

The **Knowledge Manager** service provides a comprehensive knowledge management system for AI agents and applications.

## Key Features

- **Knowledge Namespaces**: Organize knowledge into isolated, access-controlled namespaces
- **Terms & Definitions**: Define domain vocabulary with aliases, examples, and context hints
- **Relationships**: Create semantic relationships between terms
- **Rules**: Define constraints, incentives, and logical procedures
- **Versioning**: Track changes with full revision history
- **Multi-tenancy**: Support for tenant isolation and public/private namespaces

## API Endpoints

### Namespaces

- `POST /api/namespaces` - Create a new namespace
- `GET /api/namespaces` - List namespaces
- `GET /api/namespaces/{id}` - Get namespace details
- `PUT /api/namespaces/{id}` - Update namespace
- `DELETE /api/namespaces/{id}` - Delete namespace

### Terms

- `POST /api/namespaces/{id}/terms` - Add a term
- `GET /api/namespaces/{id}/terms` - List terms
- `GET /api/namespaces/{id}/terms/{term_id}` - Get term details
- `PUT /api/namespaces/{id}/terms/{term_id}` - Update term
- `DELETE /api/namespaces/{id}/terms/{term_id}` - Remove term

## Authentication

The API supports dual authentication:

- **Session-based**: OAuth2/OIDC via Keycloak (for UI)
- **Bearer token**: JWT tokens (for API/service clients)
