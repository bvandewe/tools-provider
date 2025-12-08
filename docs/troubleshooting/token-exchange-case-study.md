# Token Exchange Troubleshooting Case Study

This document captures real-world debugging patterns and root cause analysis for token exchange issues in the MCP Tools Provider development environment.

!!! abstract "Learning Objective"
    By studying these case studies, developers will understand the **temporal evolution of debugging expertise** and avoid common pitfalls when working with OAuth2 Token Exchange (RFC 8693) in a containerized environment.

## Executive Summary

Token exchange failures in development environments typically fall into **three categories**, discovered in a predictable order based on implementation phase:

| Phase | Problem Category | Discovery Trigger |
|-------|------------------|-------------------|
| 1. Basic Connectivity | URL Confusion (External vs Internal) | First attempt to integrate services |
| 2. Configuration Management | Stale Keycloak Configuration | Modifying realm after initial setup |
| 3. Advanced OAuth2 Flows | Missing Audience Mapper | Implementing token exchange feature |

---

## Case Study 1: URL Confusion (External vs Internal)

### Scenario

A developer tests token exchange from their host machine using `curl`, expecting it to work the same way as when called from within a Docker container.

### Symptoms

```bash
# From host machine
$ curl -X POST "http://keycloak:8080/realms/tools-provider/protocol/openid-connect/token" \
    -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
    ...

curl: (6) Could not resolve host: keycloak
```

### Root Cause

The Docker network is **isolated**. Hostnames like `keycloak` are only resolvable from within the Docker network.

```
┌─────────────────────────────────────────────────────────────────────┐
│  NETWORK TOPOLOGY                                                   │
└─────────────────────────────────────────────────────────────────────┘

HOST MACHINE                          DOCKER NETWORK (tools-provider-net)
┌──────────────┐                      ┌──────────────────────────────┐
│              │                      │                              │
│  Browser     │ ──────────────────►  │  Keycloak (keycloak:8080)   │
│  curl        │   localhost:8041     │       ↓                      │
│              │                      │  App (app:8080)              │
│              │                      │       ↓                      │
│  ❌ Cannot   │                      │  Redis (redis:6379)          │
│  resolve     │                      │                              │
│  "keycloak"  │                      └──────────────────────────────┘
└──────────────┘

```

### Resolution

**Understand the two URL contexts:**

| Context | URL | Used By |
|---------|-----|---------|
| External | `http://localhost:8041` | Browser, host `curl` |
| Internal | `http://keycloak:8080` | Docker containers |

**In code** (from `keycloak_token_exchanger.py:796`):

```python
# Correctly prefers internal URL when running in Docker
keycloak_url=app_settings.keycloak_url_internal or app_settings.keycloak_url,
```

**Testing from host:**

```bash
# ✅ Use external URL when testing from host
curl -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" ...
```

### Key Learning

> **The code running inside Docker must use internal URLs. The browser/developer testing from outside must use external URLs.**

---

## Case Study 2: Stale Keycloak Configuration

### Scenario

A developer modifies `tools-provider-realm-export.json` to add a new client scope, restarts Keycloak, but the changes don't appear.

### Symptoms

```bash
# Developer adds new client scope to realm export
$ vim deployment/keycloak/tools-provider-realm-export.json

# Restarts Keycloak
$ docker compose restart keycloak

# Checks Keycloak Admin Console
# ❌ New client scope is NOT there!
```

### Root Cause

Keycloak's realm import only runs on **first startup**. The H2 database is persisted in a Docker volume.

```yaml
# docker-compose.yml
keycloak:
  volumes:
    - keycloak_data:/opt/keycloak/data  # ← Persists database!
    - ./deployment/keycloak/tools-provider-realm-export.json:/opt/keycloak/data/import/...
```

**Timeline:**

```
Day 1: docker compose up
       → Keycloak imports realm from JSON
       → Realm saved to keycloak_data volume ✅

Day 2: Developer modifies tools-provider-realm-export.json
       → docker compose restart keycloak
       → Keycloak sees existing H2 database
       → SKIPS import (realm already exists) ❌
```

### Resolution

**Force re-import by removing the volume:**

```bash
# Option 1: Remove volumes and recreate
docker compose down -v
docker compose up

# Option 2: Use Makefile target (if available)
make keycloak-reset
```

**Or manually apply changes via Keycloak Admin Console:**

1. Navigate to `http://localhost:8041`
2. Login as `admin/admin`
3. Manually create/modify the client scope

### Key Learning

> **Keycloak realm import is idempotent on first boot only. To apply JSON changes, you must delete the persisted volume.**

### Makefile Best Practice

```makefile
# Add to Makefile for easy Keycloak reset
keycloak-reset:
    docker compose stop keycloak
    docker volume rm tools-provider_keycloak_data || true
    docker compose up -d keycloak
    @echo "⏳ Waiting for Keycloak to import realm..."
    @sleep 15
    @echo "✅ Keycloak reset complete"
```

---

## Case Study 3: Missing Audience Mapper

### Scenario

Token exchange is implemented, but fails with "invalid subject token" even though the user is authenticated correctly.

### Symptoms

```bash
# User authenticates successfully
$ curl -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
    -d "grant_type=password" \
    -d "client_id=tools-provider-public" \
    -d "username=admin" \
    -d "password=test" \
    | jq -r '.access_token'

# Token obtained ✅

# Token exchange fails
$ curl -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
    -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
    -d "client_id=tools-provider-token-exchange" \
    -d "client_secret=..." \
    -d "subject_token=$TOKEN" \
    -d "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
    -d "audience=pizzeria-backend"

# ❌ Error: "invalid_token" or "Client not allowed to exchange"
```

### Root Cause

The **subject token** (user's access token) must have the token exchange client in its `aud` (audience) claim. This is a security requirement of RFC 8693 Token Exchange.

**Decode the token to verify:**

```bash
$ echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq '.aud'

# Expected:
["account", "tools-provider-token-exchange"]

# Actual (broken):
["account"]  # ← Missing tools-provider-token-exchange!
```

### Resolution

**Add an audience mapper to the agent-facing client:**

1. Navigate to **Keycloak Admin Console** → **Clients** → `tools-provider-public`
2. Go to **Client scopes** → `tools-provider-public-dedicated`
3. Click **Add mapper** → **By configuration** → **Audience**
4. Configure:
   - **Name**: `audience-token-exchange`
   - **Included Client Audience**: `tools-provider-token-exchange`
   - **Add to access token**: `ON`

**Or add to realm export JSON:**

```json
{
  "clientId": "tools-provider-public",
  "protocolMappers": [
    {
      "name": "audience-token-exchange",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-audience-mapper",
      "config": {
        "included.client.audience": "tools-provider-token-exchange",
        "access.token.claim": "true"
      }
    }
  ]
}
```

### Security Explanation

```
┌─────────────────────────────────────────────────────────────────────┐
│  WHY AUDIENCE VALIDATION MATTERS                                    │
└─────────────────────────────────────────────────────────────────────┘

Without audience check:
- ANY service with client credentials could exchange ANY user's token
- Tokens issued for Service A could be hijacked by Service B
- Complete breakdown of the delegation security model

With audience check:
- Token exchange client validates: "Am I in this token's audience?"
- If NO → Reject (unauthorized)
- If YES → Proceed with exchange
```

### Key Learning

> **The subject token's `aud` claim must include the token exchange client. This is a security feature, not a bug.**

---

## Diagnostic Checklist

When token exchange fails, work through this checklist in order:

### 1. Network Connectivity

```bash
# From inside container
docker exec tools-provider-app curl -s http://keycloak:8080/health | jq

# From host
curl -s http://localhost:8041/health | jq
```

### 2. Keycloak Configuration State

```bash
# Check if realm exists
curl -s http://localhost:8041/realms/tools-provider | jq '.realm'

# List clients
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8041/admin/realms/tools-provider/clients | jq '.[].clientId'
```

### 3. Token Audience

```bash
# Decode and check audience
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq '{aud, azp, sub}'
```

### 4. Client Configuration

```bash
# Check token exchange client attributes
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8041/admin/realms/tools-provider/clients?clientId=tools-provider-token-exchange" \
  | jq '.[0].attributes'

# Expected:
# { "standard.token.exchange.enabled": "true" }
```

### 5. Circuit Breaker State

```bash
# Check if circuit breaker is open
curl -s http://localhost:8040/api/admin/circuit-breakers \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Historical Context

!!! warning "Keycloak Version Evolution"
    This project has evolved through multiple Keycloak versions. Some older documentation may reference outdated configuration.

| Version | Token Exchange Config | Notes |
|---------|----------------------|-------|
| **Keycloak 24** (Legacy) | Required `KC_FEATURES=token-exchange` | Fine-grained permissions needed |
| **Keycloak 26+** (Current) | Enabled by default | Use `standard.token.exchange.enabled` attribute |

**Always refer to `docker-compose.yml` as the source of truth for current versions.**

---

## Related Documentation

- [Keycloak Token Exchange Setup Guide](../security/keycloak-token-exchange-setup.md)
- [Circuit Breaker Guide](./circuit-breaker.md)
- [Session Management Architecture](../security/session-management.md)
- [System Integration](../architecture/system-integration.md)
