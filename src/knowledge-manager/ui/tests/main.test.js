/**
 * Tests for main.js utilities
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { showToast, apiRequest, formatDate } from '../src/scripts/main.js';

describe('formatDate', () => {
    it('should return "-" for null input', () => {
        expect(formatDate(null)).toBe('-');
    });

    it('should return "-" for undefined input', () => {
        expect(formatDate(undefined)).toBe('-');
    });

    it('should format a valid date string', () => {
        const result = formatDate('2025-01-15T10:30:00Z');
        expect(result).toContain('Jan');
        expect(result).toContain('15');
        expect(result).toContain('2025');
    });
});

describe('apiRequest', () => {
    beforeEach(() => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ data: 'test' }),
        });
    });

    it('should make a request with default headers', async () => {
        await apiRequest('/api/test');

        expect(fetch).toHaveBeenCalledWith(
            '/api/test',
            expect.objectContaining({
                headers: expect.objectContaining({
                    'Content-Type': 'application/json',
                }),
                credentials: 'include',
            })
        );
    });

    it('should merge custom options', async () => {
        await apiRequest('/api/test', {
            method: 'POST',
            body: JSON.stringify({ test: true }),
        });

        expect(fetch).toHaveBeenCalledWith(
            '/api/test',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ test: true }),
            })
        );
    });
});
