# TODO

## Bugs

- Grouping: fails to create group from filtered+selected tools
- Fails to compile list of tools from multiple groups

## Docs

- Update MkDocs homepage and main README
- Include "Supported features" for both apps (Tools Provider and Agent Host)
  - Hidden features: Rate Limiting, Circuit Breaker
  - UX features: Customize group (add/remove tool from a filtered view)
- Add ./docs/troubleshooting/faq.md

## Agent Host

- ~~Prevent the Keycloak IFrame from reloading the whole page (at a minimum prevent this to happen when user a conversation is active and particularly if user is actively typing in the message-input)~~ ✅ Implemented draft preservation and protected session mode

## Tools Provider

- Add support for Group composition where a user may

- Add admin function to drop + rebuild read models (drop mongodb + recreate persistent sub from start)
- Add admin function to consult/manage user claims to keycloak
- Emit cloudevent when token exchange was performed?
- ~~Add support for OpenAI API (use Cisco Circuit, ChatGPT, Mistral, ...)~~
