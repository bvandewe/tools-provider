# TODO

## Bugs

- [ ] Do not emit cloudevent `user.loggedin.v1` when token refreshed

- [ ] HTTP Basic is unknown?

2025-12-13 01:36:07,101 DEBUG    neuroglia.mediation.mediator:1043 🔍 MEDIATOR DEBUG: Successfully resolved ExecuteToolCommandHandler from registry

2025-12-13 01:36:07,101 DEBUG    neuroglia.mediation.mediator:1183 Found 3 pipeline behaviors for ExecuteToolCommand

2025-12-13 01:36:07,104 DEBUG    grpc._cython.cygrpc:625 [_cygrpc] Loaded running loop: id(loop)=140127715525696

2025-12-13 01:36:07,114 WARNING  application.services.tool_executor:441 Unknown auth mode: AuthMode.HTTP_BASIC

2025-12-13 01:36:07,115 DEBUG    application.services.tool_executor:981 Upstream request: GET https://labs-stg.sj.ccie.cisco.com/reservations/v3/lab_session⁠

Headers: {}

Body: None

2025-12-13 01:36:07,978 DEBUG    application.services.tool_executor:1001 Upstream response: 401

Body: {"errors":[{"code":"ERR_UNAUTHORIZED","status":401,"title":"Unauthorized","detail":"Unauthorized"}]}


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
