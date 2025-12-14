# TODO

## Bugs

- [ ] Add ability to expose authorized remote MCP servers
- [ ] Do not emit cloudevent `user.loggedin.v1` when token refreshed

- [x] HTTP Basic is unknown?
- [x] Evaluate Python code in sandbox fails

## Features

### Sources

- [ ] Add MCP source (external MCP server integrated in to the Authorized toolset)

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
