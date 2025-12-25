/**
 * Managers Module - UI State Management Layer
 *
 * Provides class-based managers for UI state management.
 * All managers are singleton instances that can be imported directly.
 *
 * @module managers
 */

// Core UI Managers
export { UIManager, uiManager } from './UIManager.js';
export { StatsManager, statsManager } from './StatsManager.js';
export { NavigationManager, navigationManager, Pages } from './NavigationManager.js';

// Data Managers
export { NamespaceManager, namespaceManager } from './NamespaceManager.js';

// Page Managers
export { DashboardPageManager, dashboardPageManager } from './DashboardPageManager.js';
export { NamespacesPageManager, namespacesPageManager } from './NamespacesPageManager.js';
export { TermsPageManager, termsPageManager } from './TermsPageManager.js';
export { AdminPageManager, adminPageManager } from './AdminPageManager.js';

// Legacy - ViewManager (deprecated, use NavigationManager)
export { ViewManager, viewManager } from './ViewManager.js';
