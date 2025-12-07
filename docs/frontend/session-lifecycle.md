# Frontend Session Lifecycle Management

This document describes the frontend session management system that provides consistent SSO session handling across both **tools-provider** and **agent-host** applications.

## Overview

The session manager implements comprehensive session lifecycle management:

- **Activity tracking** - Monitors user interactions (mouse, keyboard, touch, scroll, click)
- **Idle timeout detection** - Warns users before session expires due to inactivity
- **Background token refresh** - Keeps Keycloak session alive when user is active
- **OIDC Session Management iframe** - Detects cross-app logout via Keycloak
- **Graceful expiration** - Redirects to login when session expires

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Frontend (Browser)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │ Activity        │    │ Idle Detection  │    │ Token Refresh   │      │
│  │ Tracking        │───▶│ & Warning Modal │    │ (every 4 min)   │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│         │                       │                      │                 │
│         ▼                       ▼                      ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Session Manager                              │    │
│  │  - lastActivityTime                                              │    │
│  │  - idleCheckInterval (10s)                                       │    │
│  │  - tokenRefreshInterval (4min)                                   │    │
│  │  - sessionCheckInterval (5s)                                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│         │                       │                      │                 │
│         ▼                       ▼                      ▼                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │ OIDC Session    │    │ Backend API     │    │ Backend API     │      │
│  │ Iframe          │    │ /api/auth/me    │    │ /api/auth/      │      │
│  │ (Keycloak)      │    │                 │    │ refresh         │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Keycloak                                       │
│  - ssoSessionIdleTimeout: 1800s (30 min)                                │
│  - accessTokenLifespan: 300s (5 min)                                    │
│  - check_session_iframe endpoint                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Configuration

Session settings are fetched from the backend via `/api/auth/session-settings`:

```json
{
  "keycloak_url": "http://localhost:8041",
  "realm": "tools-provider",
  "client_id": "tools-provider-public",
  "sso_session_idle_timeout_seconds": 1800,
  "session_expiration_warning_minutes": 2,
  "check_session_iframe": "http://localhost:8041/realms/tools-provider/protocol/openid-connect/login-status-iframe.html"
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_EXPIRATION_WARNING_MINUTES` | 2 | Minutes before idle timeout to show warning modal |
| `AGENT_HOST_SESSION_EXPIRATION_WARNING_MINUTES` | 2 | Same for agent-host |

The idle timeout itself (`sso_session_idle_timeout_seconds`) is fetched from Keycloak to ensure consistency.

## Components

### 1. Activity Tracking

The session manager tracks the following user activity events:

```javascript
const ACTIVITY_EVENTS = [
    'mousedown',
    'mousemove',
    'keydown',
    'keypress',
    'scroll',
    'touchstart',
    'touchmove',
    'click',
    'focus',
];
```

Each event updates `lastActivityTime` to the current timestamp.

### 2. Idle Detection

Every 10 seconds, the idle check compares current time against `lastActivityTime`:

```javascript
function checkIdleStatus() {
    const idleSeconds = getIdleTimeSeconds();
    const warningThresholdSeconds =
        config.ssoSessionIdleTimeoutSeconds -
        config.sessionExpirationWarningMinutes * 60;

    if (idleSeconds >= warningThresholdSeconds) {
        showIdleWarning();
    }
}
```

**Example with default settings:**

- Idle timeout: 1800s (30 minutes)
- Warning threshold: 1800 - 120 = 1680s (28 minutes)
- Warning shows when user is idle for 28+ minutes
- User has 2 minutes to click "Continue"

### 3. Warning Modal

When the warning threshold is reached, a Bootstrap modal appears:

![Session Warning Modal](../assets/session-warning-modal.png)

The modal features:

- **Countdown timer** - Shows remaining time (e.g., "1:45")
- **Static backdrop** - Cannot be dismissed by clicking outside
- **Continue button** - Extends session via token refresh

```html
<div class="modal-body text-center">
    <i class="bi bi-clock display-1 text-warning"></i>
    <p class="lead">Your session will expire due to inactivity.</p>
    <p class="text-muted">
        Time remaining: <span id="warning-countdown" class="fw-bold fs-4">1:45</span>
    </p>
</div>
<div class="modal-footer justify-content-center">
    <button class="btn btn-primary btn-lg" id="extend-session-btn">
        <i class="bi bi-arrow-repeat me-2"></i>
        Continue
    </button>
</div>
```

### 4. Token Refresh

Background token refresh runs every 4 minutes when the user is active:

```javascript
// Only refresh if user was recently active (within last 5 minutes)
const idleMinutes = getIdleTimeMinutes();
if (idleMinutes < 5 && !isPaused) {
    await performTokenRefresh();
}
```

This calls `POST /api/auth/refresh` which:

1. Retrieves session from Redis
2. Uses refresh token to get new access token from Keycloak
3. Updates session with new tokens
4. Resets Keycloak's idle timer

### 5. OIDC Session Management Iframe

For cross-app logout detection, the session manager creates a hidden iframe pointing to Keycloak's `check_session_iframe` endpoint:

```javascript
function initializeSessionIframe() {
    sessionIframe = document.createElement('iframe');
    sessionIframe.id = 'keycloak-session-iframe';
    sessionIframe.style.display = 'none';
    sessionIframe.src = config.checkSessionIframe;
    document.body.appendChild(sessionIframe);

    window.addEventListener('message', handleSessionIframeMessage);

    // Check backend session every 5 seconds
    sessionCheckInterval = setInterval(() => {
        checkBackendSession();
    }, 5000);
}
```

When Keycloak detects a session state change (e.g., logout from another app), it sends a postMessage that triggers a backend session validation.

> **Note:** This implementation does NOT use the `keycloak-js` library to avoid bundler compatibility issues with Parcel. Instead, it implements the OIDC Session Management spec manually using the postMessage API.

## Session States

```
┌──────────────┐     authenticate      ┌──────────────┐
│   Logged     │ ◀─────────────────── │   Logged     │
│   Out        │                       │   In         │
└──────────────┘                       └──────────────┘
       ▲                                      │
       │                                      │
       │                                      ▼
       │                               ┌──────────────┐
       │                               │   Active     │
       │                               │   (tracking) │
       │                               └──────────────┘
       │                                      │
       │                           idle > threshold
       │                                      │
       │                                      ▼
       │                               ┌──────────────┐
       │         timeout               │   Warning    │
       └────────────────────────────── │   Shown      │
       │                               └──────────────┘
       │                                      │
       │                              click "Continue"
       │                                      │
       │                                      ▼
       │                               ┌──────────────┐
       │                               │   Extended   │─────────┐
       │                               │   (refresh)  │         │
       │                               └──────────────┘         │
       │                                                        │
       │                                                        │
       └────────────────────────────────────────────────────────┘
                        cross-app logout detected
```

## Usage

### Starting Session Monitoring

In **tools-provider** (`src/ui/src/scripts/ui/auth.js`):

```javascript
import { startSessionMonitoring } from '../core/session-manager.js';

// After successful authentication
startSessionMonitoring();
```

In **agent-host** (`agent-host/ui/src/scripts/app.js`):

```javascript
import { startSessionMonitoring, stopSessionMonitoring } from './core/session-manager.js';

class ChatApp {
    async checkAuth() {
        // ... validate session ...

        // Start session monitoring with expiration callback
        await startSessionMonitoring(() => {
            this.logout();
        });
    }

    async logout() {
        stopSessionMonitoring();
        // ... logout logic ...
    }
}
```

### Stopping Session Monitoring

Always call `stopSessionMonitoring()` on logout to clean up:

```javascript
import { stopSessionMonitoring } from '../core/session-manager.js';

function logout() {
    stopSessionMonitoring();
    window.location.href = '/api/auth/logout';
}
```

### Debugging

Use `getSessionInfo()` to inspect current session state:

```javascript
import { getSessionInfo } from '../core/session-manager.js';

console.log(getSessionInfo());
// {
//   idleTimeSeconds: 125.5,
//   idleTimeoutSeconds: 1800,
//   warningMinutes: 2,
//   isWarningShown: false,
//   isPaused: false,
//   isInitialized: true,
//   keycloakUrl: "http://localhost:8041",
//   realm: "tools-provider",
//   clientId: "tools-provider-public"
// }
```

## Backend API Endpoints

### GET /api/auth/session-settings

Returns session configuration for the frontend.

**Response:**

```json
{
  "keycloak_url": "http://localhost:8041",
  "realm": "tools-provider",
  "client_id": "tools-provider-public",
  "sso_session_idle_timeout_seconds": 1800,
  "session_expiration_warning_minutes": 2,
  "check_session_iframe": "http://localhost:8041/realms/tools-provider/protocol/openid-connect/login-status-iframe.html"
}
```

### POST /api/auth/refresh

Refreshes the OAuth2 tokens using the stored refresh token.

**Response (success):**

```json
{
  "status": "refreshed"
}
```

**Response (failure):**

- `401 Unauthorized` - Session expired or invalid

### GET /api/auth/me

Returns current user info, used to validate session status.

**Response (authenticated):**

```json
{
  "sub": "user-uuid",
  "preferred_username": "admin",
  "email": "admin@example.com",
  "roles": ["admin", "manager"]
}
```

**Response (not authenticated):**

- `401 Unauthorized`

## File Locations

| App | File | Description |
|-----|------|-------------|
| tools-provider | `src/ui/src/scripts/core/session-manager.js` | Session manager module |
| tools-provider | `src/ui/static/silent-check-sso.html` | OIDC silent check page |
| tools-provider | `src/api/controllers/auth_controller.py` | Backend auth endpoints |
| agent-host | `agent-host/ui/src/scripts/core/session-manager.js` | Session manager module |
| agent-host | `agent-host/ui/static/silent-check-sso.html` | OIDC silent check page |
| agent-host | `agent-host/src/api/controllers/auth_controller.py` | Backend auth endpoints |

## Keycloak Configuration

The session behavior depends on Keycloak realm settings:

| Setting | Value | Description |
|---------|-------|-------------|
| SSO Session Idle | 30 minutes | Time before idle session expires |
| SSO Session Max | 10 hours | Maximum session lifetime |
| Access Token Lifespan | 5 minutes | JWT access token validity |
| Client Session Idle | 0 (use realm) | Client-specific override |

To modify these settings:

1. Open Keycloak Admin Console
2. Navigate to Realm Settings → Sessions
3. Adjust timeouts as needed

## Troubleshooting

### Session expires too quickly

1. Check Keycloak SSO Session Idle timeout
2. Verify token refresh is working (`POST /api/auth/refresh`)
3. Ensure activity events are being tracked (check browser console)

### Warning modal not showing

1. Verify `SESSION_EXPIRATION_WARNING_MINUTES` is set
2. Check that `/api/auth/session-settings` returns valid data
3. Ensure session manager is initialized (`startSessionMonitoring()` called)

### Cross-app logout not working

1. Verify `check_session_iframe` URL is accessible
2. Check browser console for CORS errors
3. Ensure both apps use the same Keycloak realm

### Token refresh failing

1. Check Keycloak logs for token refresh errors
2. Verify refresh token hasn't expired
3. Ensure client configuration allows refresh tokens

## Related Documentation

- [Session Management with Redis](../security/session-management.md) - Backend session storage
- [Authentication Flows](../security/authentication-flows.md) - OAuth2/OIDC flows
- [Keycloak Token Exchange Setup](../security/keycloak-token-exchange-setup.md) - Token exchange configuration
