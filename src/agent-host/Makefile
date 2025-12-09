.PHONY: help install test lint format clean build-ui dev-ui run run-debug

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)agent-host - Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install Python dependencies with Poetry
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	poetry install
	@echo "$(GREEN)Dependencies installed!$(NC)"

install-ui: ## Install Node.js dependencies for UI
	@echo "$(BLUE)Installing UI dependencies...$(NC)"
	cd ui && npm install
	@echo "$(GREEN)UI dependencies installed!$(NC)"

build-ui: ## Build frontend assets
	@echo "$(BLUE)Building frontend assets...$(NC)"
	cd ui && npm run build
	@echo "$(GREEN)Frontend assets built!$(NC)"

dev-ui: ## Start UI development server with hot-reload
	@echo "$(BLUE)Starting UI development server...$(NC)"
	cd ui && npm run dev

setup: install install-ui build-ui ## Complete setup for development
	@echo "$(GREEN)✅ Setup complete!$(NC)"

##@ Running

run: build-ui ## Run the application locally
	@echo "$(BLUE)Starting agent-host application...$(NC)"
	@echo "$(GREEN)Access at: http://localhost:8001$(NC)"
	PYTHONPATH=. poetry run uvicorn main:create_app --factory --host 0.0.0.0 --port 8001 --reload

run-debug: build-ui ## Run with debug logging
	@echo "$(BLUE)Starting agent-host with debug logging...$(NC)"
	LOG_LEVEL=DEBUG PYTHONPATH=. poetry run uvicorn main:create_app --factory --host 0.0.0.0 --port 8001 --reload --log-level debug

##@ Testing & Quality

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	poetry run pytest

lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	poetry run ruff check .

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	poetry run black .

##@ Cleanup

clean: ## Clean up generated files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf ui/.parcel-cache 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"
