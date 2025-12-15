.PHONY: help up down logs build setup test lint format clean

# Default target
.DEFAULT_GOAL := help

# ==============================================================================
# VARIABLES
# ==============================================================================

# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Docker settings
COMPOSE_FILE := docker-compose.yml
COMPOSE := docker-compose -f $(COMPOSE_FILE)

# App directories
TOOLS_PROVIDER_DIR := src/tools-provider
AGENT_HOST_DIR := src/agent-host
UPSTREAM_SAMPLE_DIR := src/upstream-sample

# Port settings with defaults (can be overridden in .env)
APP_PORT ?= 8040
KEYCLOAK_PORT ?= 8041
EVENTSTORE_PORT ?= 8042
MONGODB_EXPRESS_PORT ?= 8043
REDIS_PORT ?= 8045
EVENT_PLAYER_PORT ?= 8046
OTEL_COLLECTOR_PORT_GRPC ?= 4417
OTEL_COLLECTOR_PORT_HTTP ?= 4418
REDIS_COMMANDER_PORT ?= 8048

# URLs
APP_URL := http://localhost:$(APP_PORT)
API_DOCS_URL := $(APP_URL)/api/docs
REDIS_URL := redis://localhost:$(REDIS_PORT)
KEYCLOAK_URL := http://localhost:$(KEYCLOAK_PORT)
EVENTSTORE_URL := http://localhost:$(EVENTSTORE_PORT)
EVENT_PLAYER_URL := http://localhost:$(EVENT_PLAYER_PORT)
MONGO_EXPRESS_URL := http://localhost:$(MONGODB_EXPRESS_PORT)
REDIS_COMMANDER_URL := http://localhost:$(REDIS_COMMANDER_PORT)

# Documentation settings
DOCS_SITE_NAME ?= "Starter App"
DOCS_SITE_URL ?= "https://bvandewe.github.io/starter-app"
DOCS_DEV_PORT ?= 8000

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ==============================================================================
# HELP
# ==============================================================================

##@ General

help: ## Display this help message
	@echo "$(BLUE)Tools Provider - Root Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)This is the orchestration Makefile. Each app has its own Makefile:$(NC)"
	@echo "  cd $(TOOLS_PROVIDER_DIR) && make help"
	@echo "  cd $(AGENT_HOST_DIR) && make help"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# ==============================================================================
# DOCKER COMMANDS
# ==============================================================================

##@ Docker

build: ## Build Docker images for all services
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(COMPOSE) build

up: ## Start services in the background
	@echo "$(BLUE)Starting Docker services...$(NC)"
	$(COMPOSE) up -d
	@echo "$(GREEN)Services started!$(NC)"
	@$(MAKE) urls

down: ## Stop and remove services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	$(COMPOSE) down
	@echo "$(GREEN)Services stopped!$(NC)"

start: ## Start existing containers
	$(COMPOSE) start

stop: ## Stop running containers
	$(COMPOSE) stop

restart: ## Restart all services
	$(COMPOSE) restart

restart-service: ## Restart a single Docker service (usage: make restart-service SERVICE=service_name)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Please specify SERVICE=<service_name>$(NC)"; \
		echo "Available services:"; \
		$(COMPOSE) config --services; \
		exit 1; \
	fi
	$(COMPOSE) up -d --force-recreate $(SERVICE)

rebuild-service: ## Rebuild a single service without cache and restart if running (usage: make rebuild-service SERVICE=service_name)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Please specify SERVICE=<service_name>$(NC)"; \
		echo "Available services:"; \
		$(COMPOSE) config --services; \
		exit 1; \
	fi
	@echo "$(BLUE)Rebuilding $(SERVICE) without cache...$(NC)"
	$(COMPOSE) build --no-cache $(SERVICE)
	@echo "$(BLUE)Restarting $(SERVICE)...$(NC)"
	$(COMPOSE) up -d --force-recreate $(SERVICE)
	@echo "$(GREEN)$(SERVICE) rebuilt and restarted!$(NC)"

dev: ## Build and start services with live logs
	$(COMPOSE) up --build

rebuild: ## Rebuild services from scratch without cache
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d --force-recreate

logs: ## Show logs from all services
	$(COMPOSE) logs -f

logs-app: ## Show logs from tools-provider service only
	$(COMPOSE) logs -f tools-provider

logs-agent: ## Show logs from agent-host service only
	$(COMPOSE) logs -f agent-host

ps: ## Show running containers
	$(COMPOSE) ps

docker-clean: ## Stop services and remove all volumes (WARNING: removes all data)
	@echo "$(RED)WARNING: This will remove all containers, volumes, and data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down -v; \
		echo "$(GREEN)Cleanup complete!$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled.$(NC)"; \
	fi

urls: ## Display application and service URLs
	@echo ""
	@echo "$(YELLOW)Application URLs:$(NC)"
	@echo "  Main App:        $(APP_URL)"
	@echo "  API Docs:        $(API_DOCS_URL)"
	@echo ""
	@echo "$(YELLOW)Infrastructure:$(NC)"
	@echo "  Keycloak Admin:  $(KEYCLOAK_URL) (admin/admin)"
	@echo "  EventStore:      $(EVENTSTORE_URL) (admin/changeit)"
	@echo "  Redis:           $(REDIS_URL)"
	@echo "  Event Player:    $(EVENT_PLAYER_URL)"
	@echo ""
	@echo "$(YELLOW)Management Tools:$(NC)"
	@echo "  Mongo-Express:    $(MONGO_EXPRESS_URL) (admin@admin.com/admin)"
	@echo "  Redis Commander:  $(REDIS_COMMANDER_URL)"

# ==============================================================================
# DATABASE MANAGEMENT
# ==============================================================================

##@ Database Management

reset-keycloak-db: ## Reset Keycloak database (re-imports realm from export files)
	@echo "$(YELLOW)Resetting Keycloak database...$(NC)"
	$(COMPOSE) down keycloak
	docker volume rm tools-provider_keycloak_data 2>/dev/null || true
	$(COMPOSE) up keycloak -d
	@echo "$(GREEN)Keycloak database reset!$(NC)"

redis-flush: ## Flush all Redis data (clears sessions, forces re-login)
	$(COMPOSE) exec redis redis-cli FLUSHALL
	@echo "$(GREEN)Redis flushed!$(NC)"

reset-eventstore-db: ## Reset EventStoreDB (clears all events)
	$(COMPOSE) down eventstore
	docker volume rm tools-provider_eventstore_data 2>/dev/null || true
	$(COMPOSE) up eventstore -d
	@echo "$(GREEN)EventStoreDB reset!$(NC)"

reset-mongodb: ## Reset MongoDB (clears read model)
	$(COMPOSE) down mongodb mongo-express
	docker volume rm tools-provider_mongo_data 2>/dev/null || true
	$(COMPOSE) up mongodb mongo-express -d
	@echo "$(GREEN)MongoDB reset!$(NC)"

reset-app-data: ## Reset all app data (EventStore, MongoDB, Redis) - preserves Keycloak
	@echo "$(RED)WARNING: This will clear EventStore, MongoDB, and Redis!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down eventstore mongodb mongo-express; \
		docker volume rm tools-provider_eventstore_data 2>/dev/null || true; \
		docker volume rm tools-provider_mongo_data 2>/dev/null || true; \
		$(COMPOSE) exec redis redis-cli FLUSHALL || true; \
		$(COMPOSE) up eventstore mongodb mongo-express -d; \
		echo "$(GREEN)All app data reset!$(NC)"; \
	fi

reconcile: ## Delete EventStore subscription and restart app to replay events
	@curl -s -X DELETE "http://localhost:2113/subscriptions/\$$ce-tools_provider/tools-provider-consumer-group" \
		-u admin:changeit -H "Content-Type: application/json" || true
	@echo "$(GREEN)Ready - restart the app to replay all events$(NC)"

# ==============================================================================
# APP-SPECIFIC COMMANDS (DELEGATED)
# ==============================================================================

##@ App Development (delegated to app Makefiles)

setup-tools-provider: ## Setup tools-provider app
	@echo "$(BLUE)Setting up tools-provider...$(NC)"
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) setup

setup-agent-host: ## Setup agent-host app
	@echo "$(BLUE)Setting up agent-host...$(NC)"
	cd $(AGENT_HOST_DIR) && $(MAKE) setup

setup: setup-tools-provider setup-agent-host ## Setup all apps
	@echo "$(GREEN)✅ All apps setup complete!$(NC)"

test: ## Run tools-provider tests
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) test

test-domain: ## Run tools-provider domain tests
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) test-domain

test-application: ## Run tools-provider application tests
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) test-application

test-cov: ## Run tools-provider tests with coverage
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) test-cov

lint: ## Run linting on tools-provider
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) lint

format: ## Format tools-provider code
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) format

run: ## Run tools-provider locally (port 8000)
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) run

run-debug: ## Run tools-provider with debug logging
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) run-debug

run-agent: ## Run agent-host locally (port 8001)
	cd $(AGENT_HOST_DIR) && $(MAKE) run

# ==============================================================================
# CLEANUP
# ==============================================================================

##@ Cleanup

clean: ## Clean up all generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	cd $(TOOLS_PROVIDER_DIR) && $(MAKE) clean
	cd $(AGENT_HOST_DIR) && $(MAKE) clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean docker-clean ## Clean everything including Docker volumes

# ==============================================================================
# DOCUMENTATION
# ==============================================================================

##@ Documentation

docs-serve: ## Serve documentation locally with live reload
	@echo "$(BLUE)Starting documentation server at http://127.0.0.1:$(DOCS_DEV_PORT)$(NC)"
	mkdocs serve --dev-addr=127.0.0.1:$(DOCS_DEV_PORT)

docs-build: ## Build documentation site
	mkdocs build --site-dir site

docs-deploy: ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy --force

# ==============================================================================
# INFORMATION
# ==============================================================================

##@ Information

env-check: ## Check environment requirements
	@echo "$(BLUE)Checking environment...$(NC)"
	@command -v python3.12 >/dev/null 2>&1 || { echo "$(RED)❌ Python 3.12 not found$(NC)"; exit 1; }
	@command -v poetry >/dev/null 2>&1 || { echo "$(RED)❌ Poetry not found$(NC)"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "$(RED)❌ Node.js not found$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ Docker not found$(NC)"; exit 1; }
	@echo "$(GREEN)✅ All requirements satisfied!$(NC)"

info: ## Show project information
	@echo "$(BLUE)Tools Provider - Project Information$(NC)"
	@echo ""
	@echo "$(YELLOW)Apps:$(NC)"
	@echo "  tools-provider   $(TOOLS_PROVIDER_DIR)"
	@echo "  agent-host       $(AGENT_HOST_DIR)"
	@echo "  upstream-sample  $(UPSTREAM_SAMPLE_DIR)"
	@echo ""
	@echo "$(YELLOW)Docker Services:$(NC)"
	@echo "  tools-provider   http://localhost:$(APP_PORT)"
	@echo "  Keycloak         http://localhost:$(KEYCLOAK_PORT) (admin/admin)"
	@echo "  EventStore       http://localhost:$(EVENTSTORE_PORT) (admin/changeit)"
	@echo "  MongoDB Express  http://localhost:$(MONGODB_EXPRESS_PORT)"
	@echo ""
	@echo "$(YELLOW)Local Development:$(NC)"
	@echo "  cd $(TOOLS_PROVIDER_DIR) && make run   # Port 8000"
	@echo "  cd $(AGENT_HOST_DIR) && make run       # Port 8001"
