# 📖 Documentation Structure

This documentation covers two applications:

- **Tools Provider** - MCP tool aggregation and management
- **Agent Host** - Conversational AI interface

---

## Core Documentation

### [Architecture](architecture/overview.md)

System architecture and design patterns:

- **[Agent Host Architecture](architecture/agent-host-architecture.md)** - Conversation aggregate, templates, flows
- **[Conversation Flows](architecture/conversation-flows.md)** - ReAct and Proactive flow diagrams
- CQRS with Mediator pattern
- Event Sourcing with Neuroglia
- Dependency injection patterns

### [Development](development/testing.md)

Developer workflows and implementation guides:

- **[Agent Host Implementation Guide](development/agent-host-implementation-guide.md)** - Step-by-step walkthrough for developers new to AI agents
- Makefile command reference
- Testing strategies
- Code quality tools

### [Frontend](frontend/web-components.md)

UI development and user guides:

- WebComponents architecture
- Build process (Parcel, Nunjucks)
- **[Conversation Guide](frontend/conversation-guide.md)** - User guide for chat features
- Session lifecycle management

### [Security](security/authentication-flows.md)

Security, authentication and authorization:

- Session management with Redis
- OAuth2/OIDC with Keycloak
- JWT token validation
- Role-based access control (RBAC)

### [Infrastructure](infrastructure/docker-environment.md)

Environment setup and deployment:

- Docker Compose stack
- MongoDB, Redis, EventStoreDB configuration
- Keycloak setup
- Observability with OpenTelemetry

### [Troubleshooting](troubleshooting/common-issues.md)

Common problems and solutions:

- Known issues and workarounds
- Environment debugging
- Build troubleshooting

---

## Archive (Historical Specs)

The **Archive** section contains superseded design documents and implementation plans. These are kept for historical reference but **do not reflect the current implementation**.

!!! warning "Archived Documents"
    Documents in the Archive section describe designs that were either:

    - **Superseded** - Replaced by newer designs
    - **Partially implemented** - Only some features were built
    - **Not implemented** - Design was not pursued
    
    Always refer to the [Architecture](architecture/overview.md) section for current system design.
