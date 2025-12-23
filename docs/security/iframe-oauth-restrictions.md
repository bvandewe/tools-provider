# OAuth Authentication in Embedded IFrames

This document describes the security constraints and solutions for embedding external OAuth-protected content within the Agent Host iframe widget.

## 🚫 The Problem

When the `ax-iframe-widget` loads external content protected by OAuth2 (via oauth2-proxy, Keycloak, or similar), the authentication flow **fails with 403 Forbidden** errors:

```
GET https://example.com/oauth2/callback?state=...&session_state=...&code=... 403 (Forbidden)
```

This is **by design** - OAuth providers implement multiple security measures that prevent authentication flows from completing inside iframes.

## 🔒 Why OAuth Fails in IFrames

### 1. X-Frame-Options / Content-Security-Policy Headers

OAuth providers (including oauth2-proxy and Keycloak) send security headers that prevent their pages from being framed:

```http
X-Frame-Options: DENY
# or
X-Frame-Options: SAMEORIGIN
# or
Content-Security-Policy: frame-ancestors 'none';
```

These headers are **clickjacking protections** mandated by security best practices. They prevent malicious sites from embedding login pages in invisible iframes to steal credentials.

### 2. SameSite Cookie Restrictions

OAuth flows rely on session cookies to maintain state between redirects. Modern browsers enforce `SameSite` cookie policies:

- **SameSite=Strict**: Cookies never sent in cross-site contexts (iframe is cross-site)
- **SameSite=Lax**: Cookies sent only with top-level navigation (not iframe loads)
- **SameSite=None**: Requires `Secure` flag and explicit configuration

When the iframe loads content from a different origin, cookies may be blocked entirely.

### 3. Third-Party Cookie Deprecation

Browsers are actively deprecating third-party cookies:

| Browser | Status |
|---------|--------|
| Safari | Blocked by default since 2020 |
| Firefox | Blocked by default with ETP |
| Chrome | Phasing out (Privacy Sandbox) |

This breaks OAuth state management in cross-origin iframes.

### 4. oauth2-proxy Frame Protection

oauth2-proxy explicitly blocks framing by default. The callback endpoint validates that requests come from top-level navigation, not embedded contexts.

## ✅ Recommended Solutions

### Option 1: Pre-Authentication (Recommended for SSO)

If the user is already authenticated in the parent application and both apps share the same identity provider:

1. **Share authentication context** - Pass tokens via `postMessage` or URL parameters
2. **Use token exchange** - Exchange parent's token for a child-app-specific token
3. **Cookie sharing** - If same-domain, authentication cookies may be shared

**Implementation:**

```javascript
// Parent app sends token to iframe via postMessage
iframe.contentWindow.postMessage({
    type: 'auth-token',
    token: currentAccessToken
}, targetOrigin);
```

### Option 2: Popup-Based Authentication

Open the OAuth flow in a popup window instead of the iframe:

```javascript
// Detect auth required (iframe fires event on 401/403)
iframeWidget.addEventListener('ax-iframe-error', (e) => {
    if (e.detail.authRequired) {
        // Open auth in popup
        const popup = window.open(authUrl, 'oauth-popup', 'width=500,height=600');

        // Listen for completion
        window.addEventListener('message', (event) => {
            if (event.data.type === 'oauth-complete') {
                // Reload iframe with auth complete
                iframeWidget.reload();
            }
        });
    }
});
```

### Option 3: Same-Origin Reverse Proxy

Route iframe content through your own domain using a reverse proxy:

```
User's Browser
    │
    └─► https://your-app.com/embedded/external-app/*
            │
            └─► (nginx/traefik proxy) ─► https://external-app.com/*
```

This makes the iframe content same-origin, avoiding all cross-origin restrictions.

**nginx configuration:**

```nginx
location /embedded/external-app/ {
    proxy_pass https://external-app.com/;
    proxy_set_header Host external-app.com;
    proxy_set_header X-Real-IP $remote_addr;
    # Pass through auth cookies
    proxy_pass_request_headers on;
}
```

### Option 4: Configure oauth2-proxy to Allow Framing (⚠️ Not Recommended)

If you control the oauth2-proxy configuration and accept the security trade-offs:

```yaml
# oauth2-proxy config (REDUCES SECURITY)
--skip-provider-button=true
--set-xauthrequest=true
```

**Ingress/nginx headers:**

```yaml
# Allow framing from specific origins only
add_header Content-Security-Policy "frame-ancestors https://your-parent-app.com";
# Or disable protection entirely (NOT RECOMMENDED)
add_header X-Frame-Options "ALLOWALL";
```

> ⚠️ **Security Warning**: Allowing framing of authentication pages exposes users to clickjacking attacks. Only use this option for internal/trusted applications with additional mitigations in place.

## 🎯 Decision Matrix

| Scenario | Recommended Solution |
|----------|---------------------|
| Same IdP, SSO available | Pre-authentication with token sharing |
| Different IdP, high security | Popup-based authentication |
| Full infrastructure control | Same-origin reverse proxy |
| Internal/trusted apps only | Configure oauth2-proxy (with caution) |
| Public-facing, high security | Do not embed OAuth-protected content |

## 📋 Implementation Checklist

When embedding OAuth-protected content in iframes:

- [ ] Verify the target application's `X-Frame-Options` and CSP headers
- [ ] Check cookie `SameSite` policies
- [ ] Test in browsers with third-party cookie blocking enabled
- [ ] Implement error detection in iframe widget for auth failures
- [ ] Choose and implement an appropriate authentication strategy
- [ ] Document the security trade-offs for your deployment

## 🔗 Related Documentation

- [Authentication Flows](./authentication-flows.md)
- [Session Management](./session-management.md)
- [Keycloak Token Exchange Setup](./keycloak-token-exchange-setup.md)

## 📚 External References

- [OWASP Clickjacking Defense](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)
- [MDN: X-Frame-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options)
- [oauth2-proxy Configuration](https://oauth2-proxy.github.io/oauth2-proxy/docs/configuration/overview)
- [RFC 6749: OAuth 2.0 Security Considerations](https://datatracker.ietf.org/doc/html/rfc6749#section-10)
