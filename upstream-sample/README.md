# Pizzeria Backend - Sample Upstream Service

A minimal FastAPI service demonstrating **Role-Based Access Control (RBAC)** with Keycloak integration and **MongoDB persistence**. This service simulates a pizzeria backend API for demo and testing purposes.

## Purpose

This sample upstream service is used to demonstrate:

- JWT Bearer token validation with Keycloak
- Role-based endpoint authorization
- Token exchange scenarios with the main Tools Provider application
- MongoDB persistence for menu items and orders

## Architecture

- **FastAPI** - Web framework with automatic OpenAPI documentation
- **MongoDB** - Persistent storage for menu items and orders (database: `pizzeria`)
- **Motor** - Async MongoDB driver for non-blocking database operations
- **Keycloak** - Authentication and role-based access control

## Roles & Permissions

The service maps Keycloak realm roles to pizzeria business roles:

| Keycloak Role | Pizzeria Role | Permissions |
|---------------|---------------|-------------|
| `user` | Customer | View menu, place orders, pay online |
| `developer` | Chef | View orders, start cooking, complete orders |
| `manager` | Manager | View orders, edit menu, view analytics |
| `admin` | Admin | Full access to all endpoints |

## API Endpoints

### Menu (`/api/menu`)

| Method | Endpoint | Required Role | Description |
|--------|----------|---------------|-------------|
| GET | `/api/menu` | Any authenticated | List all menu items |
| GET | `/api/menu/{item_id}` | Any authenticated | Get menu item details |
| POST | `/api/menu` | manager, admin | Add new menu item |
| PUT | `/api/menu/{item_id}` | manager, admin | Update menu item |
| DELETE | `/api/menu/{item_id}` | manager, admin | Remove menu item |

### Orders (`/api/orders`)

| Method | Endpoint | Required Role | Description |
|--------|----------|---------------|-------------|
| GET | `/api/orders` | developer, manager, admin | List all orders (kitchen/management) |
| GET | `/api/orders/my` | user, admin | List customer's own orders |
| GET | `/api/orders/{order_id}` | user (own), developer, manager, admin | Get order details |
| POST | `/api/orders` | user, admin | Place a new order |
| POST | `/api/orders/{order_id}/pay` | user (own), admin | Pay for an order |

### Kitchen (`/api/kitchen`)

| Method | Endpoint | Required Role | Description |
|--------|----------|---------------|-------------|
| GET | `/api/kitchen/queue` | developer, admin | View pending orders |
| POST | `/api/kitchen/orders/{order_id}/start` | developer, admin | Start cooking an order |
| POST | `/api/kitchen/orders/{order_id}/complete` | developer, admin | Mark order as ready |

## Running Locally

```bash
# From the upstream-sample directory
pip install -e .
uvicorn app.main:create_app --factory --reload --port 8051
```

## Running with Docker Compose

The service is included in the main `docker-compose.yml`:

```bash
# From the project root
docker-compose up pizzeria-backend
```

Access the API:

- API: http://localhost:8051
- OpenAPI Docs: http://localhost:8051/docs

## Authentication

All endpoints require a valid JWT Bearer token from Keycloak:

```bash
# Get a token (using Resource Owner Password Grant for testing)
TOKEN=$(curl -s -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=tools-provider-public" \
  -d "username=user" \
  -d "password=test" | jq -r '.access_token')

# Call an endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8051/api/menu
```

## Test Users

| Username | Password | Roles | Pizzeria Access |
|----------|----------|-------|-----------------|
| user | test | user | Customer operations |
| developer | test | developer | Chef/Kitchen operations |
| manager | test | manager | Management operations |
| admin | test | admin, manager | Full access |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_URL` | `http://localhost:8041` | Keycloak server URL (external) |
| `KEYCLOAK_URL_INTERNAL` | `http://keycloak:8080` | Keycloak URL (Docker internal) |
| `KEYCLOAK_REALM` | `tools-provider` | Keycloak realm name |
| `LOG_LEVEL` | `INFO` | Logging level |
