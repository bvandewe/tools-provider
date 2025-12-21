# TODO

## Protocol Cleanup (Completed ✅)

- [x] **Remove ChatService legacy streaming methods** - Removed ~1650 lines of legacy streaming code from `application/services/chat_service.py`. Kept only essential methods: `set_model_override`, `get_or_create_conversation`, `get_tools`, `tool_to_llm_definition`, `clear_conversation`, `delete_conversation`, `get_conversations`, `configure`.
- [x] **Frontend handler consolidation** - Deleted `protocol/message-handlers/` directory. All protocol handlers now use event bus pattern in `handlers/`.
- [x] **Clean up protocol/message-router.js** - Already clean; only contains routing logic with no legacy handlers.
- [x] **Note**: ChatService is still needed for `get_tools()` and `_conversation_repo` access. ConversationOrchestrator handles all WebSocket streaming.

- [ ] Provide LLM with Conversation tools (repeat previous item when user didnt respond appropriately)
- [ ] Instrument all application handlers with metrics/traces

## Frontend

- [ ] Fix UI widgets when switching between Session types and reactive Conversation
- [ ] Improve "tools call details" modal with clear sequence, timestamp and request/response tabs
- [ ] Improve "available tools" modal with vertical overflow and quick search/filter
- [ ] Add option to user profile dropdown (in nav bar) to delete all user's Conversations
- [ ] Group Conversation's action icons in 3-vertical-dots icon
- [ ] Add auto-focus to Chat input field (so user can type directly when the page loaded initially and when clicking on New Conversation)

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
