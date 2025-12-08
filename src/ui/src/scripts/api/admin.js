/**
 * Admin API Client
 *
 * Handles API calls for administrative operations like circuit breaker management.
 */

import { apiRequestJson } from './client.js';

/**
 * Get all circuit breaker states
 * @returns {Promise<Object>} Circuit breaker states
 */
export async function getCircuitBreakers() {
    return apiRequestJson('/api/admin/circuit-breakers');
}

/**
 * Reset a circuit breaker
 * @param {string} type - 'token_exchange' or 'tool_execution'
 * @param {string|null} key - For tool_execution, the source key or 'all'
 * @returns {Promise<Object>} Reset result
 */
export async function resetCircuitBreaker(type, key = null) {
    const body = { type };
    if (key) {
        body.key = key;
    }

    return apiRequestJson('/api/admin/circuit-breakers/reset', {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

/**
 * Get token exchange health status
 * @returns {Promise<Object>} Health status
 */
export async function getTokenExchangeHealth() {
    return apiRequestJson('/api/admin/health/token-exchange');
}
