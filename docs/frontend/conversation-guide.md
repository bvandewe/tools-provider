# Conversation Guide

**Audience:** End Users
**Status:** Current Features (December 2025)

---

## Getting Started

The Agent Host provides an AI-powered chat interface where you can:

- Have conversations with AI assistants
- Use specialized agents for different tasks
- Complete structured assessments and quizzes
- Execute tools and view results

### Accessing the Chat

1. Navigate to the application URL
2. Sign in with your credentials (Keycloak)
3. You'll see the chat interface with available agents

---

## Types of Conversations

### 1. Standard Chat (Reactive)

In standard chat, **you start the conversation** by typing a message.

**How it works:**

1. Type your question or request in the input box
2. Press Enter or click Send
3. The AI processes your request (you may see tool executions)
4. The response streams in real-time

**Tips:**

- Be specific in your requests
- You can ask follow-up questions
- The AI remembers context from earlier in the conversation

### 2. Agent-Driven Conversations (Proactive)

Some agents initiate conversations with **structured content**. These are useful for:

- Quizzes and assessments
- Surveys and feedback collection
- Guided workflows

**How it works:**

1. Click on an agent tile (e.g., "Knowledge Quiz")
2. The agent presents the first question or prompt
3. Respond using the provided widgets
4. The agent continues with the next item

---

## Interactive Widgets

Instead of typing, some agents present interactive widgets:

### Multiple Choice

Select one or more options from a list.

**Keyboard shortcuts:**

- `1-9` - Quick select option by number
- `Enter` - Submit selection
- `Tab` - Navigate between options

### Free Text

Type a longer response when the agent needs detailed input.

**Features:**

- Character count indicator
- Auto-resize as you type
- Markdown support in some cases

### Code Editor

For technical questions, you may get a code editor with:

- Syntax highlighting
- Line numbers
- Language-appropriate formatting

---

## Conversation Features

### Managing Conversations

**Sidebar Actions:**

- **New Chat** - Start a fresh conversation
- **Conversation List** - Click any past conversation to continue it
- **Rename** - Click the title to edit
- **Delete** - Remove a conversation from history

### Tool Execution

When the AI uses tools (like searching, calculating, or reading files), you'll see:

1. **Tool Card** - Shows which tool is running
2. **Arguments** - What parameters were used
3. **Result** - The output (may be summarized for large data)

### Progress Indicator

In agent-driven conversations, a progress bar shows:

- Current item number
- Total items
- Time remaining (if timed)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message (in chat input) |
| `Shift+Enter` | New line in message |
| `Escape` | Cancel current request |
| `Ctrl+/` | Show keyboard shortcuts |

---

## Troubleshooting

### Message not sending?

- Check your internet connection
- Ensure you're signed in (look for your name in the header)
- Try refreshing the page

### AI response seems stuck?

- Look for a spinning indicator
- Click "Cancel" if available
- Start a new conversation

### Widget not responding?

- Click directly on the option
- Try using keyboard shortcuts
- Report persistent issues to support

---

## Privacy & Data

- Conversations are stored securely
- Only you and shared users can access your conversations
- Admins may have access for troubleshooting
- Tool executions use your permissions

---

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Look for error messages in red
3. Contact your administrator with:
   - What you were trying to do
   - Any error messages shown
   - The conversation ID (if available)
