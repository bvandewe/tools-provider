// Main application entry point
import 'bootstrap';
import '../styles/main.scss';

// Legacy web components (for backward compatibility)
import './web-components/index.js';

// New modular components
import './components/index.js';
import './pages/index.js';

// Core modules
import { initTheme } from './core/theme.js';

// Initialize theme before app loads
initTheme();

// Main app
import './app.js';
