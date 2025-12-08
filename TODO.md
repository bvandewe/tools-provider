# TODO

## Tools Provider

## Docs

- Update

## Agent Host

- add conversation info/details modal with indicator of token/chunk/bytes/messages counts per conversation, incl. tools used per agent message if any
- ensure that when user logs in the agent-host, a new conversation is created by default. If its already the case
- add same copy agent's response to clipboard to user's prompts
- add ability to pin conversations
- add ability to share conversations (with specific users in Realm with unique URL)
- run healthcheck when user first login turn health icon (heart) green when

## Tools Provider

- P3: improve UI' UX: whenever displaying on any Entity's detail modal and in main views: always 'humanized' toolName (e.g
create_order_api_orders_post to `Order on menu`!), always include cross-reference URL links between (m)any Entity's modal details (Source vs Tool vs Group vs Policy) to greatly improve cross navigation between any Entity

- P3: unify the UI experience between both agent-host and tools-provider apps:
  - use agent-host as the reference UI layout (header)
  - hide user name from page' header similarly to how agent-host UI does it (show a user profile icon/button with a bootstrap nav dropdown)

- P4: add ./docs/troubleshooting/faq.md


- add admin function to drop + rebuild read models (drop mongodb + recreate persistent sub from start)
- add admin function to manage user claims to keycloak
- emit cloudevent when token exchange was performed?

- ~~add indicator when circuit breaker is open for a source and function to force close it~~ ✅ Done: `/api/admin/circuit-breakers` endpoint + Admin UI page
- ~~emit cloudevent when circuit breaker state changes~~ ✅ Done: `circuit_breaker.opened/closed/half_opened.v1` events
- ~~add admin functions to reset DB (mongo + redis)~~ ✅ Done: see Makefile
- ~~add circuit breaker status indicator to UI (sources page)~~ ✅ Done: New Admin page with circuit breaker dashboard
