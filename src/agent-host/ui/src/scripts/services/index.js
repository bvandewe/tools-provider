/**
 * Services Module - External Services and Side Effects
 *
 * Provides services for interacting with external systems:
 * - ApiService: HTTP API client
 * - AuthService: Authentication and session management
 * - ThemeService: Theme switching
 * - ModalService: Bootstrap modal management
 * - SettingsService: Admin settings
 *
 * MIGRATION NOTE: Class-based services are the new standard.
 * All services now follow the singleton pattern with explicit initialization.
 *
 * @module services
 */

// =============================================================================
// CLASS-BASED SERVICES (Preferred)
// =============================================================================

// API Service
export { ApiService, apiService, api } from './ApiService.js';

// Auth Service
export { AuthService, authService } from './AuthService.js';

// Theme Service
export { ThemeService, themeService } from './ThemeService.js';

// Modal Service
export { ModalService, modalService } from './ModalService.js';

// Settings Service
export { SettingsService, settingsService } from './SettingsService.js';
