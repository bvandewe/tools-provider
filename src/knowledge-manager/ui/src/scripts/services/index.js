/**
 * Services Module - External Services and Side Effects
 *
 * Provides services for interacting with external systems:
 * - ApiService: HTTP API client
 * - AuthService: Authentication and session management
 * - ThemeService: Theme switching
 * - ModalService: Bootstrap modal management
 *
 * All services follow the singleton pattern with explicit initialization.
 *
 * @module services
 */

// API Service
export { ApiService, apiService, api } from './ApiService.js';

// Auth Service
export { AuthService, authService } from './AuthService.js';

// Theme Service
export { ThemeService, themeService } from './ThemeService.js';

// Modal Service
export { ModalService, modalService, showToast } from './ModalService.js';
