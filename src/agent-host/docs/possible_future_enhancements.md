# Possible Future Enhancements

This document captures potential improvements and features that were considered but not implemented in the current phase.

## Session Initiation Methods

### Currently Implemented: Agent Selector in Header ✅

A dropdown in the header that lets users switch between session modes:

- **Chat** (default) - Normal conversation mode
- **Learning** - Proactive learning sessions with category selection
- **Thought** - AI-guided brainstorming sessions

### Alternative Approaches Considered

#### 1. Slash Commands

**Effort:** Low
**Description:** Allow users to start sessions via chat commands like `/learn algebra`

**Pros:**

- Minimal UI changes required
- Familiar to power users (Slack-style)
- Can include parameters inline

**Cons:**

- Not discoverable for new users
- Requires documentation/help system
- No visual feedback before execution

**Example:**

```
/learn algebra        # Start algebra learning session
/learn geometry 5     # Start geometry with 5 questions
/thought              # Start thought session
/validation           # Start validation workflow
```

#### 2. New Conversation Modal Enhancement

**Effort:** Medium
**Description:** Add session type selector when clicking "New Conversation"

**Pros:**

- Integrates with existing workflow
- Clear separation between chat and sessions
- Can show session descriptions

**Cons:**

- Adds friction to starting regular chats
- Modal complexity increases
- Users may skip/ignore options

**Mockup:**

```
┌─────────────────────────────────────┐
│  New Conversation                   │
├─────────────────────────────────────┤
│  ○ Regular Chat                     │
│  ○ Learning Session                 │
│      Category: [Algebra ▾]          │
│      Questions: [5 ▾]               │
│  ○ Thought Session                  │
│  ○ Validation Workflow              │
├─────────────────────────────────────┤
│  [Cancel]              [Start]      │
└─────────────────────────────────────┘
```

#### 3. Sidebar Section for Sessions

**Effort:** High
**Description:** Dedicated sidebar section showing active/past sessions separately from conversations

**Pros:**

- Clear visual separation
- Easy to resume sessions
- Shows session progress/status

**Cons:**

- Major UI restructure needed
- Sidebar may become cluttered
- Mobile experience affected

**Mockup:**

```
┌─────────────────────┐
│ Conversations       │
│ ├─ Chat with AI     │
│ ├─ Project planning │
│ └─ + New Chat       │
├─────────────────────┤
│ Learning Sessions   │
│ ├─ Algebra (3/5) ▶  │
│ ├─ Python (Done) ✓  │
│ └─ + New Session    │
└─────────────────────┘
```

#### 4. Welcome Screen Session Tiles

**Effort:** Medium
**Description:** Add session type tiles to the welcome screen

**Pros:**

- Highly discoverable
- Visual and inviting
- Good for onboarding

**Cons:**

- Only visible on welcome screen
- Can't start session mid-conversation
- Takes up screen real estate

**Mockup:**

```
┌─────────────────────────────────────────────┐
│         Welcome to Agent Host               │
│                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 💬      │ │ 📚      │ │ 💭      │       │
│  │ Chat    │ │ Learn   │ │ Think   │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                                             │
│  Or type a message to start chatting...    │
└─────────────────────────────────────────────┘
```

---

## Widget Enhancements

### Rich Code Editor

- Syntax highlighting with CodeMirror/Monaco
- Multiple file support
- Test case execution feedback
- Diff view for comparing answers

### Image/Diagram Widget

- Allow users to draw diagrams
- Upload images as answers
- Canvas-based input for geometry

### Voice Input Widget

- Speech-to-text for answers
- Pronunciation exercises
- Language learning support

### Timer Widget

- Timed quizzes
- Countdown display
- Auto-submit on timeout

---

## Session Features

### Progress Persistence

- Save session progress to database
- Resume incomplete sessions
- Show completion percentage

### Adaptive Difficulty

- Track correct/incorrect answers
- Adjust question difficulty dynamically
- Personalized learning paths

### Gamification

- Points and scoring
- Streaks for consecutive correct answers
- Achievements/badges
- Leaderboards (optional)

### Session Templates

- Pre-configured session types
- Share session templates
- Import/export templates

---

## Analytics & Reporting

### Learning Analytics Dashboard

- Questions answered over time
- Accuracy by category
- Time spent per question
- Improvement trends

### Session Export

- Export session results as PDF
- Share results via link
- Integration with LMS systems

---

## Integration Ideas

### External Question Sources

- Import questions from JSON/CSV
- Connect to quiz APIs
- LMS integration (Canvas, Moodle)

### Collaborative Sessions

- Multi-user sessions
- Real-time collaboration
- Teacher/student mode

### AI-Generated Questions

- Generate questions from topic
- Personalized question generation
- Difficulty adjustment

---

## Technical Improvements

### Offline Support

- Cache questions locally
- Queue responses when offline
- Sync on reconnect

### Performance Optimizations

- Lazy load question banks
- Preload next question
- Stream large code outputs

### Testing Enhancements

- Visual regression tests for widgets
- Load testing for concurrent sessions
- Accessibility audit automation
