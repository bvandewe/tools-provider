# TODO

## Bugs

- [ ] Do not emit cloudevent `user.loggedin.v1` when token refreshed

## Features

### Sources

- [ ] Add MCP source (external MCP server integrated in to the Authorized toolset)

### Tools

- [ ] Add server-side pagination/filtering to support large amount of tools

### Groups

- [ ] fails to create group from filtered+selected tools
- [ ] streamline how groups are built (select tool with pick n choose in addition to via selector)

### Policies



### Admin

- [ ] Add admin function to drop + rebuild read models (drop mongodb + recreate persistent sub from start)
- [ ] Add admin function to consult/manage user claims to keycloak
- [ ] Emit cloudevent when token exchange was performed?
- [x] Add support for OpenAI API (use Cisco Circuit, ChatGPT, Mistral, ...)
