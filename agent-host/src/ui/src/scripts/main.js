/**
 * Agent Host Chat Application
 * Entry point - imports and initializes all modules
 */

import * as bootstrap from 'bootstrap';

// Make bootstrap available globally for modals
window.bootstrap = bootstrap;

// Import web components (self-registering)
import './components/ChatMessage.js';
import './components/ToolCallCard.js';

// Import services
import { initTheme } from './services/theme.js';

// Import main application
import { ChatApp } from './app.js';

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme service (handles button binding internally)
    initTheme();

    window.chatApp = new ChatApp();
    window.chatApp.init();
});
