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

- P1: CRITICAL help refine my thoughts about a replacement to our current traditional static web-based "Exam Delivery System" where humans' professional high-stake skills validation session (called Exams) are digitized as a statically defined (read-only) web-based experience leading a invaluable accreditation (which has a variable `marketDifferentiator` and `potentialImpact` depending on the "ExamLevel" and "CertificationTrack".

Define user-centric `Agentic experience` including THREE AI Personas (THE "Human Alter Ego", THE "Robot Tutor" and THE "AI Validator")

- All Assistants DRIVE interactions with the end-user, prompting either a "`Thought` Session", a "`Learning` Session" or "`Validation` Session" AND **CRITICAL** NEVER allowing the user to deviate the conversation!!!

- All "Sessions" are persisted as separate "`Conversations`"

- All Sessions deliver a sequence of "`Items`" presenting a "simple" interactive/realtime ChatBot-like SPA Web Page (including `AgenticUiComponents` similar to UI Widgets that can be positioned in an infinite "Canvas" like web UI)

- `UiWidgets` are persisted as Semantic Graphs with various edge' types (deliverySequence, entityRelationship, socialRelationship, {semanticCategory}) that enables efficient runtime queries when defining then next Item.

- Assistant's SystemPrompts are "Extremely Rigid", recursively running their `AgenticIntention` until their `confidenceLevel` (self-assessed) and optionally their externally-signed `overallScore` are converged and meeting all of their `passingCriteria`.

  - `ThoughtSession` ends when user explicitely asked to (this is the Human mind)

  - `LearningSession` ends when LearningCriterias are met (this is the Tutor' Robot mind)

  - `ValidationSession` ends when ValidationCriteria are met (this is the AI' "mind with vision, mission and values")
    - `UserPrompt` may request the user to justify its choices, explain logical sequence and dependency tree in own words, confirm/infirm `evaluationPrompt` (that may contain false/true/blurry/nonsense `Statements`)
    - Measures (instrumented by Otel, CloudEvent, UnstructLogs, EventLoops) all interactions to help define next Iteration (on the "next item selection" process)


- P3: improve UI' UX: whenever displaying on any Entity's detail modal and in main views: always 'humanized' toolName (e.g
create_order_api_orders_post to `Order on menu`!), always include cross-reference URL links between (m)any Entity's modal details (Source vs Tool vs Group vs Policy) to greatly improve cross navigation between any Entity

- add admin function to drop + rebuild read models (drop mongodb + recreate persistent sub from start)
- add admin function to manage user claims to keycloak
- emit cloudevent when token exchange was performed?

- ~~add indicator when circuit breaker is open for a source and function to force close it~~ ✅ Done: `/api/admin/circuit-breakers` endpoint + Admin UI page
- ~~emit cloudevent when circuit breaker state changes~~ ✅ Done: `circuit_breaker.opened/closed/half_opened.v1` events
- ~~add admin functions to reset DB (mongo + redis)~~ ✅ Done: see Makefile
- ~~add circuit breaker status indicator to UI (sources page)~~ ✅ Done: New Admin page with circuit breaker dashboard
