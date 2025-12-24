# Knowledge Manager Makefile
# Following the same pattern as tools-provider and agent-host

.PHONY: setup install run run-debug test test-unit test-domain test-application test-cov lint format clean build-ui watch-ui help

# Default target
help:
	@echo "Knowledge Manager - Development Commands"
	@echo ""
	@echo "Setup & Install:"
	@echo "  make setup          - Full setup (install deps + build UI)"
	@echo "  make install        - Install Python dependencies"
	@echo ""
	@echo "Run:"
	@echo "  make run            - Run the application"
	@echo "  make run-debug      - Run with DEBUG log level"
	@echo ""
	@echo "Test:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-domain    - Run domain layer tests"
	@echo "  make test-application - Run application layer tests"
	@echo "  make test-cov       - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linter (ruff)"
	@echo "  make format         - Format code (black + ruff)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove cache files"
	@echo ""
	@echo "UI:"
	@echo "  make build-ui       - Build the UI"
	@echo "  make watch-ui       - Watch UI for changes"

# Setup
setup: install build-ui
	@echo "✅ Setup complete!"

install:
	@echo "📦 Installing Python dependencies..."
	poetry install --no-root
	@echo "✅ Dependencies installed!"

# Run
run:
	@echo "🚀 Starting Knowledge Manager..."
	poetry run python -m uvicorn main:create_app --factory --host 127.0.0.1 --port 8003 --reload

run-debug:
	@echo "🐛 Starting Knowledge Manager in DEBUG mode..."
	LOG_LEVEL=DEBUG poetry run python -m uvicorn main:create_app --factory --host 127.0.0.1 --port 8003 --reload

# Test
test:
	@echo "🧪 Running all tests..."
	poetry run pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	poetry run pytest tests/ -v -m "unit"

test-domain:
	@echo "🧪 Running domain tests..."
	poetry run pytest tests/domain/ -v

test-application:
	@echo "🧪 Running application tests..."
	poetry run pytest tests/application/ -v

test-cov:
	@echo "📊 Running tests with coverage..."
	poetry run pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

# Code Quality
lint:
	@echo "🔍 Running linter..."
	poetry run ruff check .

format:
	@echo "✨ Formatting code..."
	poetry run black .
	poetry run ruff check . --fix

# UI Build
build-ui:
	@echo "🏗️  Building UI..."
	cd ui && npm install && npm run build
	@echo "✅ UI build complete!"

watch-ui:
	@echo "👀 Watching UI for changes..."
	cd ui && npm run watch

# Cleanup
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	cd ui && rm -rf node_modules .parcel-cache src/tmp_build 2>/dev/null || true
	@echo "✅ Clean complete!"
