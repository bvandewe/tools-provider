#!/usr/bin/env python3
"""
Test script for token exchange flow with pizzeria-backend.

This script demonstrates the complete RFC 8693 token exchange flow:
1. Authenticate as a user via Keycloak (direct access grant)
2. Register the pizzeria source with default_audience
3. Execute a tool that triggers token exchange
4. Verify the upstream service receives a properly scoped token

Usage:
    # Start services first
    make up

    # Run the test script
    python scripts/test_token_exchange.py

Prerequisites:
    - Keycloak running with tools-provider realm imported
    - EventStoreDB running
    - MongoDB running
    - tools-provider running (make run or make run-debug)
    - pizzeria-backend running
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8041")
TOOLS_PROVIDER_URL = os.getenv("TOOLS_PROVIDER_URL", "http://localhost:8040")
PIZZERIA_OPENAPI_URL = os.getenv("PIZZERIA_OPENAPI_URL", "http://pizzeria-backend:8080/openapi.json")
REALM = os.getenv("KEYCLOAK_REALM", "tools-provider")
CLIENT_ID = os.getenv("CLIENT_ID", "tools-provider-backend")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "tools-provider-backend-secret-change-in-production")  # pragma: allowlist secret

# Test users (from realm export) - pragma: allowlist secret
TEST_USERS = {
    "admin": {"username": "admin", "password": "test", "expected_role": "admin"},  # pragma: allowlist secret
    "manager": {"username": "manager", "password": "test", "expected_role": "manager"},  # pragma: allowlist secret
    "developer": {"username": "developer", "password": "test", "expected_role": "developer"},  # pragma: allowlist secret
    "user": {"username": "user", "password": "test", "expected_role": "user"},  # pragma: allowlist secret
}


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step: int, description: str) -> None:
    """Print a step indicator."""
    print(f"\n[Step {step}] {description}")
    print("-" * 50)


def print_json(data: Any, indent: int = 2) -> None:
    """Print formatted JSON."""
    print(json.dumps(data, indent=indent, default=str))


async def get_user_token(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Get an access token for a user via direct access grant."""
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    response = await client.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code != 200:
        print(f"❌ Failed to get token: {response.status_code}")
        print(response.text)
        sys.exit(1)

    token_data = response.json()
    return token_data["access_token"]


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (for inspection only)."""
    import base64

    # Split the token
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    # Decode payload (second part)
    payload = parts[1]
    # Add padding if needed
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding

    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)


async def register_pizzeria_source(client: httpx.AsyncClient, token: str) -> str:
    """Register the pizzeria source with token exchange enabled."""
    url = f"{TOOLS_PROVIDER_URL}/api/sources/"

    payload = {
        "name": "Pizzeria Backend",
        "url": PIZZERIA_OPENAPI_URL,
        "source_type": "openapi",
        "default_audience": "pizzeria-backend",  # This triggers token exchange!
        "validate_url": False,  # Skip validation as we're using internal URL
    }

    response = await client.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to register source: {response.status_code}")
        print(response.text)
        sys.exit(1)

    result = response.json()
    print("✅ Source registered successfully")
    return result.get("id") or result.get("data", {}).get("id")


async def refresh_inventory(client: httpx.AsyncClient, token: str, source_id: str) -> None:
    """Refresh the tool inventory for the source."""
    url = f"{TOOLS_PROVIDER_URL}/api/sources/{source_id}/refresh"

    response = await client.post(
        url,
        json={"force": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code not in [200, 201, 202]:
        print(f"❌ Failed to refresh inventory: {response.status_code}")
        print(response.text)
        sys.exit(1)

    print("✅ Inventory refreshed successfully")


async def list_tools(client: httpx.AsyncClient, token: str, source_id: str) -> list:
    """List tools from the source."""
    url = f"{TOOLS_PROVIDER_URL}/api/tools/?source_id={source_id}"

    response = await client.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code != 200:
        print(f"❌ Failed to list tools: {response.status_code}")
        print(response.text)
        return []

    tools = response.json()
    return tools.get("data", tools) if isinstance(tools, dict) else tools


async def execute_tool(client: httpx.AsyncClient, token: str, tool_id: str, arguments: dict) -> dict:
    """Execute a tool."""
    url = f"{TOOLS_PROVIDER_URL}/api/tools/{tool_id}/execute"

    response = await client.post(
        url,
        json={"arguments": arguments},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )

    return {"status_code": response.status_code, "response": response.json() if response.status_code == 200 else response.text}


async def main():
    """Main test flow."""
    print_header("Token Exchange Flow Test")
    print(f"Keycloak URL: {KEYCLOAK_URL}")
    print(f"Tools Provider URL: {TOOLS_PROVIDER_URL}")
    print(f"Pizzeria OpenAPI URL: {PIZZERIA_OPENAPI_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get admin token
        print_step(1, "Authenticate as admin user")
        admin_token = await get_user_token(client, "admin", "test")
        print("✅ Got admin token")

        # Inspect token
        token_payload = decode_jwt_payload(admin_token)
        print(f"   Subject: {token_payload.get('sub')}")
        print(f"   Username: {token_payload.get('preferred_username')}")
        print(f"   Roles: {token_payload.get('roles', [])}")
        print(f"   Audience: {token_payload.get('aud')}")

        # Check if token has token-exchange client in audience
        aud = token_payload.get("aud", [])
        if isinstance(aud, str):
            aud = [aud]
        if "tools-provider-token-exchange" in aud:
            print("   ✅ Token includes tools-provider-token-exchange in audience")
        else:
            print("   ⚠️  Token does NOT include tools-provider-token-exchange in audience")
            print("   Token exchange may fail - check Keycloak audience mapper configuration")

        # Step 2: Register pizzeria source
        print_step(2, "Register Pizzeria source with default_audience='pizzeria-backend'")
        source_id = await register_pizzeria_source(client, admin_token)
        print(f"   Source ID: {source_id}")

        # Step 3: Refresh inventory
        print_step(3, "Refresh tool inventory")
        await refresh_inventory(client, admin_token, source_id)

        # Step 4: List tools
        print_step(4, "List available tools")
        tools = await list_tools(client, admin_token, source_id)
        print(f"   Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5
            name = tool.get("name", tool.get("tool_name", "unknown"))
            print(f"   - {name}")
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more")

        # Step 5: Execute a tool (get menu)
        print_step(5, "Execute 'getApiMenu' tool (triggers token exchange)")

        # Find the menu tool
        menu_tool = None
        for tool in tools:
            name = tool.get("name", tool.get("tool_name", ""))
            if "menu" in name.lower() and "get" in name.lower():
                menu_tool = tool
                break

        if menu_tool:
            tool_id = menu_tool.get("id", menu_tool.get("tool_id"))
            print(f"   Executing tool: {menu_tool.get('name', menu_tool.get('tool_name'))}")
            print(f"   Tool ID: {tool_id}")

            result = await execute_tool(client, admin_token, tool_id, {})

            if result["status_code"] == 200:
                print("   ✅ Tool execution successful!")
                print("   Response preview:")
                response_data = result["response"]
                if isinstance(response_data, dict):
                    # Pretty print first part of response
                    print_json(response_data)
            else:
                print(f"   ❌ Tool execution failed: {result['status_code']}")
                print(f"   Error: {result['response']}")
        else:
            print("   ⚠️  Could not find menu tool to test")

        # Step 6: Test different user roles
        print_step(6, "Test role-based access with different users")

        for role, user_info in [("user", TEST_USERS["user"]), ("developer", TEST_USERS["developer"])]:
            print(f"\n   Testing as '{role}' user...")
            user_token = await get_user_token(client, user_info["username"], user_info["password"])

            # Try to execute same tool
            if menu_tool:
                tool_id = menu_tool.get("id", menu_tool.get("tool_id"))
                result = await execute_tool(client, user_token, tool_id, {})

                if result["status_code"] == 200:
                    print(f"   ✅ {role}: Tool execution successful (as expected - read access)")
                else:
                    print(f"   ❌ {role}: Tool execution failed - {result['status_code']}")

        print_header("Test Complete")
        print(
            """
Summary:
--------
If all steps succeeded, token exchange is working correctly!

The flow is:
1. User authenticates → gets token with aud=['tools-provider-token-exchange', ...]
2. Tools Provider receives request with user's token
3. When executing tool with required_audience='pizzeria-backend':
   - Token exchanger exchanges user's token for pizzeria-scoped token
   - New token has aud=['pizzeria-backend'] and preserves user identity
4. Pizzeria backend receives request with properly scoped token
5. Pizzeria validates token and applies RBAC based on user's roles

To verify token exchange is happening, check the tools-provider logs for:
- "Exchanging token for audience: pizzeria-backend"
- "Token exchange successful"
"""
        )


if __name__ == "__main__":
    asyncio.run(main())
