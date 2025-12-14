# TODO

## Bugs

- [ ] Do not emit cloudevent `user.loggedin.v1` when token refreshed
- [ ] Add ability to expose authorized remote MCP servers
- [x] HTTP Basic is unknown?

## Features

### Sources

- [ ] Add MCP source (external MCP server integrated in to the Authorized toolset)

### Tools

- [ ] Add server-side pagination/filtering to support large amount of tools
- [ ] Add basic analytics and reporting (tool calls count per source over time, active sources, active users)

### Groups

- [x] add selector on HTTP Method
- [x] streamline how groups are built (select tool with pick n choose in addition to via selector)

### Policies


### Admin

- [ ] Add admin Tab to manage Data Inconsistencies
  - [ ] Run tools' diagnostic for ALL tools
  - [ ] Drop + rebuild read models (drop mongodb + recreate persistent sub from start?)
- [ ] Add admin function to consult/manage user claims to keycloak
- [ ] Emit cloudevent when token exchange was performed?

- [x] Add support for OpenAI API (use Cisco Circuit, ChatGPT, Mistral, ...)
