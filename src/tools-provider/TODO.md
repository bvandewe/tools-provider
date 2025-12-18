# TODO

## Bugs


- Expired session lead to weird page with JSON instead of the Login page!
http://localhost:8040/api/auth/callback?error=temporarily_unavailable&error_description=authentication_expired&state=uBENHnG0BYriwAfdHsp1DA&iss=http%3A%2F%2Flocalhost%3A8041%2Frealms%2Ftools-provider
{
"detail": [
{
"type": "missing",
"loc": [
"query",
"code"
],
"msg": "Field required",
"input": null
}
]
}


- [ ] Do not emit cloudevent `user.loggedin.v1` when token refreshed

- [x] HTTP Basic is unknown?
- [x] Evaluate Python code in sandbox fails

## Features

### System

- Add semantic memory with vector DB
- Add code inspection capabilities with inspect_system_component tool (for both backend and frontend)

### Sources

- [ ] Add support for OpenAPI sources with different JWT_AUTHORITY
- [x] Add MCP source (external MCP server integrated in to the Authorized toolset)

### Tools

- [ ] Add basic analytics and reporting (tool calls count per source over time, active sources, active users)
- [x] Add server-side pagination/filtering to support large amount of tools

### Groups

- [x] add selector on HTTP Method
- [x] streamline how groups are built (select tool with pick n choose in addition to via selector)

### Policies

- [ ] Add dry-run functionality to check whether a user can execute a tool
- [ ] Add verification functionality to verify whether a user can execute a tool

### Admin

- [ ] Add admin Tab to manage Data Inconsistencies
  - [ ] Run tools' diagnostic for ALL tools
  - [ ] Drop + rebuild read models (drop mongodb + recreate persistent sub from start?)
- [ ] Add admin function to consult/manage user claims to keycloak
- [ ] Emit cloudevent when token exchange was performed?

- [x] Add support for OpenAI API (use Cisco Circuit, ChatGPT, Mistral, ...)
