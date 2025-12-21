/**
 * Agent Host Chat Application
 * Entry point - imports and initializes all modules
 *
 * Module Structure (Phase 5A.2 Refactoring):
 * - core/       - Event bus, state manager
 * - utils/      - DOM helpers, formatting, storage, validation
 * - services/   - API, auth, theme, modals
 * - domain/     - Business logic (config, definition, conversation)
 * - protocol/   - WebSocket client and message handlers
 * - ui/         - UI managers and renderers
 * - widgets/    - Client action widget components
 *
 * Migration Path:
 * - Current: Uses app.js (legacy monolithic orchestrator)
 * - Future: Switch to app-v2.js for modular architecture
 *   import { ChatApp } from './app-v2.js';
 */

import * as bootstrap from 'bootstrap';

// Make bootstrap available globally for modals
window.bootstrap = bootstrap;

// Import web components (self-registering)
import './components/ChatMessage.js';
import './components/ToolCallCard.js';

// Import ALL client action widgets (self-registering)
// Display widgets
import './components/ax-text-display.js';
import './components/ax-image-display.js';
import './components/ax-chart.js';
import './components/ax-data-table.js';

// Input widgets
import './components/ax-multiple-choice.js';
import './components/ax-free-text-prompt.js';
import './components/ax-code-editor.js';
import './components/ax-slider.js';
import './components/ax-checkbox-group.js';
import './components/ax-dropdown.js';
import './components/ax-rating.js';
import './components/ax-date-picker.js';
import './components/ax-matrix-choice.js';

// Interactive widgets
import './components/ax-drag-drop.js';
import './components/ax-hotspot.js';
import './components/ax-drawing.js';

// Action & feedback widgets
import './components/ax-submit-button.js';
import './components/ax-progress-bar.js';
import './components/ax-timer.js';

// Embedded content
import './components/ax-iframe-widget.js';

// Conversation header
import './components/ax-conversation-header.js';

// Import services
import { initTheme } from './services/theme.js';

// Import main application (WebSocket-only architecture)
import { ChatApp } from './app.js';

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme service (handles button binding internally)
    initTheme();

    window.chatApp = new ChatApp();
    window.chatApp.init();
});
