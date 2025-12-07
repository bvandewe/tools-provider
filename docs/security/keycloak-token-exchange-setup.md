# Keycloak Token Exchange Configuration Guide

This document describes how to configure Keycloak for RFC 8693 Token Exchange, enabling the MCP Tools Provider to securely delegate agent identities to upstream services.

## Overview

Token Exchange allows the MCP Tools Provider to exchange an agent's access token for a new token scoped to a specific upstream service. This implements secure identity delegation without exposing the agent's original credentials to upstream services.

**Flow:**

```
Agent → MCP Provider (with Agent Token) → Keycloak (Token Exchange) → Upstream Service (with Exchanged Token)
```

## Prerequisites

- Keycloak 18+ (tested with Keycloak 24.x)
- Admin access to the Keycloak realm
- The MCP Tools Provider realm already configured (default: `tools-provider`)

## Configuration Steps

### Step 1: Create the Token Exchange Client

This client is used by the MCP Tools Provider to perform token exchange operations.

1. Navigate to **Clients** → **Create client**
2. Configure the client:
   - **Client ID**: `tools-provider-token-exchange`
   - **Client Protocol**: `openid-connect`
   - **Access Type**: `confidential`
   - **Standard Flow Enabled**: `OFF`
   - **Direct Access Grants Enabled**: `OFF`
   - **Service Accounts Enabled**: `ON`

3. Save and go to **Credentials** tab
4. Copy the **Client Secret** for your `.env` file:

   ```env
   TOKEN_EXCHANGE_CLIENT_ID=tools-provider-token-exchange
   TOKEN_EXCHANGE_CLIENT_SECRET=<copied-secret>
   ```

### Step 2: Enable Token Exchange Feature

Token Exchange must be explicitly enabled in Keycloak:

1. Navigate to **Realm Settings** → **General**
2. Ensure **Token Exchange** is enabled (this may require feature flag in older versions)

For Keycloak started with Docker:

```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    environment:
      - KC_FEATURES=token-exchange,admin-fine-grained-authz
    command: start-dev
```

### Step 3: Configure Token Exchange Permission

The token exchange client needs permission to exchange tokens on behalf of users:

1. Navigate to **Clients** → `tools-provider-token-exchange` → **Service account roles**
2. Click **Assign role**
3. Filter by client: `realm-management`
4. Assign the following roles:
   - `impersonation`
   - `manage-users` (optional, for advanced scenarios)

### Step 4: Create Upstream Service Clients (Audiences)

For each upstream service that tools can call, create a client in Keycloak:

1. Navigate to **Clients** → **Create client**
2. Configure the upstream client:
   - **Client ID**: `billing-service-api` (example)
   - **Client Protocol**: `openid-connect`
   - **Access Type**: `bearer-only` (no login flow needed)

3. Go to **Service account roles** for the token exchange client
4. Add permissions to exchange for this audience

### Step 5: Configure Client Policy for Token Exchange

Create a fine-grained authorization policy:

1. Navigate to **Clients** → `tools-provider-token-exchange` → **Authorization** tab
   (Enable authorization if not already enabled)

2. Create a **Policy**:
   - **Name**: `allow-token-exchange`
   - **Type**: `Client`
   - **Logic**: `Positive`
   - **Clients**: Select clients that can be exchanged for

3. Create a **Permission**:
   - **Name**: `token-exchange-permission`
   - **Type**: `Scope`
   - **Scopes**: `token-exchange`
   - **Apply Policy**: `allow-token-exchange`

### Alternative: Using Client Scope Mappings

For simpler setups, you can use client scope mappings:

1. Navigate to **Clients** → `tools-provider-token-exchange` → **Client scopes**
2. Add the audiences as **Assigned default client scopes**

## Environment Variables

Add these to your `.env` file:

```env
# Token Exchange Configuration
TOKEN_EXCHANGE_CLIENT_ID=tools-provider-token-exchange
TOKEN_EXCHANGE_CLIENT_SECRET=your-secret-here

# Token Exchange Tuning
TOKEN_EXCHANGE_CACHE_TTL_BUFFER=60
TOKEN_EXCHANGE_TIMEOUT=10.0

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30.0
```

## Testing Token Exchange

You can test token exchange using curl:

```bash
# 1. Get an agent token (as if logging in)
AGENT_TOKEN=$(curl -s -X POST \
  "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=tools-provider-public" \
  -d "username=johndoe" \
  -d "password=password" \
  | jq -r '.access_token')

# 2. Exchange for an upstream service token
curl -X POST \
  "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "client_id=tools-provider-token-exchange" \
  -d "client_secret=your-secret-here" \
  -d "subject_token=$AGENT_TOKEN" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "audience=billing-service-api" \
  -d "requested_token_type=urn:ietf:params:oauth:token-type:access_token"
```

## Upstream Source Configuration

When registering an upstream source, include the OAuth2 configuration that specifies the audience for token exchange:

```json
{
  "name": "Billing API",
  "url": "https://billing.example.com/openapi.json",
  "source_type": "openapi",
  "auth_type": "oauth2",
  "oauth2_client_id": "billing-service-api",
  "oauth2_token_url": "http://keycloak:8080/realms/tools-provider/protocol/openid-connect/token"
}
```

The `oauth2_client_id` becomes the `audience` parameter in token exchange requests.

## Security Best Practices

1. **Minimal Permissions**: Only grant token exchange permissions for specific audiences
2. **Short Token Lifetimes**: Configure exchanged tokens with shorter lifetimes (5-15 minutes)
3. **Audience Restriction**: Always specify the exact audience in exchange requests
4. **Scope Limiting**: Request only necessary scopes for upstream operations
5. **Audit Logging**: Enable Keycloak audit logs to track token exchanges
6. **Rate Limiting**: Implement rate limiting on the token exchange endpoint

## Troubleshooting

### Error: "Client not allowed to exchange"

The token exchange client lacks permission for the target audience:

1. Check **Service account roles** include `impersonation`
2. Verify the audience client exists
3. Check authorization policies if using fine-grained permissions

### Error: "Invalid subject token"

The agent's token is expired or malformed:

1. Verify the agent token hasn't expired
2. Check the token was issued by the correct realm
3. Ensure `subject_token_type` is correct

### Error: "Unsupported grant type"

Token exchange feature is not enabled:

1. Restart Keycloak with `KC_FEATURES=token-exchange`
2. Verify the realm has token exchange enabled

### Circuit Breaker Opens

The circuit breaker protects against Keycloak outages:

1. Check Keycloak is healthy: `curl http://localhost:8041/health`
2. Review logs for connection errors
3. Wait for recovery timeout before retrying

## Monitoring

The MCP Tools Provider exposes metrics for token exchange:

- `tools_provider.token_exchange.count` - Total exchange operations
- `tools_provider.token_exchange.errors` - Exchange failures by type
- `tools_provider.token_exchange.cache_hits` - Cache hit rate
- `tools_provider.circuit_breaker.opens` - Circuit breaker activations

## References

- [RFC 8693 - OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)
- [Keycloak Token Exchange Documentation](https://www.keycloak.org/docs/latest/securing_apps/#_token-exchange)
- [Keycloak Fine-Grained Authorization](https://www.keycloak.org/docs/latest/authorization_services/)
