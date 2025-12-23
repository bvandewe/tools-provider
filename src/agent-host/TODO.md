# TODO

## Protocol Cleanup (Completed ✅)

- [ ] Provide Agent with Conversation tools (repeat previous item when user didnt respond appropriately)
- [ ] Instrument all application handlers with metrics/traces

## Frontend

- Add new widgets:
  - date/time range selector
  - calendar (weekly, monthly)
  - treeview (e.g. blueprint topics per domain)
  - terminal output (e.g. collected output from device serial console)

- [ ] Add auto-focus to Chat input field (so user can type directly when the page loaded initially and when clicking on New Conversation)
- [ ] Fix UI widgets when switching between Session types and reactive Conversation
- [ ] Improve "tools call details" modal with clear sequence, timestamp and request/response tabs
- [ ] Add option to user profile dropdown (in nav bar) to delete all user's Conversations
- [ ] Group Conversation's action icons in 3-vertical-dots icon
- [x] Improve "available tools" modal with vertical overflow and quick search/filter

## Admin/Settings

- [ ] Improve Healthcheck to show health for OpenAI Provider next to Ollama
- [ ] Improve Agent/Session Settings

## Agents

- [ ] Add a "replay" feature to Conversation that automatically replays the user messages sequentially one-by-one
- [ ] Add client-tools
  - [ ] MCMA
  - [ ] DnD, Category DnD
  - [ ] Hotspot
  - [ ] IFrame
  - [ ] Device Console to TVp/Guacamole
- [ ] Add support for A2A

## Proactive Sessions

- [ ] Add timer when waiting user input/interactions
- [ ] Add reminder and warning when user is idle
- [ ] Add feedback provider agent for eval sessions

- [x] Resolve/clean-up OpenAI available models from Circuit API
