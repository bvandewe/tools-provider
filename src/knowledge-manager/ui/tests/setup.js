/**
 * Test setup for Vitest
 */

import { vi } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Mock bootstrap
vi.mock('bootstrap', () => ({
    default: {},
    Toast: vi.fn().mockImplementation(() => ({
        show: vi.fn(),
    })),
    Modal: vi.fn().mockImplementation(() => ({
        show: vi.fn(),
        hide: vi.fn(),
    })),
    Tooltip: vi.fn(),
}));

// Reset mocks before each test
beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
});
