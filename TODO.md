# TODO

## Tools Provider


## Agent Host

- add conversation details modal with indicator of token/chunk counts per conversation, tools used
- ensure that when user logs in the agent-host, a new conversation is created by default. If its already the case
- add same copy agent's response to clipboard to user's prompts
- add ability to pin conversations
- add ability to share conversations (with specific users in Realm with unique URL)
- run healthcheck when user first login turn health icon (heart) green when

## Tools Provider

- add indicator when circuit breaker is open for a source and function to force close it
- emit cloudevent when token exchange was performed?
- add admin functions to reset DB (mongo + redis)
- add admin function to drop + rebuild read models (drop mongodb + recreate persistent sub from start)
- add admin function to manage user claims to keycloak
