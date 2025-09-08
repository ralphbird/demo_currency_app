.PHONY: help install dev run build docker-run test quality clean setup

# Default target - shows available commands
help:
	@echo "💰 Currency Conversion API - Development Commands"
	@echo ""
	@echo "📋 Available Commands:"
	@echo "  make install  - Install dependencies with Poetry"
	@echo "  make setup    - Complete setup (install + pre-commit + demo data)"
	@echo "  make dev      - Start development server with auto-reload"
	@echo "  make run      - Start production server"
	@echo "  make build    - Build Docker container"
	@echo "  make docker-run - Build and run Docker container"
	@echo "  make test     - Run test suite with coverage"
	@echo "  make quality  - Run code quality checks (format, lint, type-check)"
	@echo "  make clean    - Clean build artifacts and caches"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup    - Set up everything for development"
	@echo "  make dev      - Start development server"
	@echo ""
	@echo "📖 Documentation:"
	@echo "  API Docs: http://localhost:8000/docs (when running)"
	@echo "  Health:   http://localhost:8000/health"

# Default target when just running 'make'
.DEFAULT_GOAL := help

# Install dependencies
install:
	@echo "📦 Installing dependencies with Poetry..."
	poetry install
	@echo "✅ Dependencies installed!"

# Complete development setup
setup: install
	@echo "🛠️  Setting up development environment..."
	poetry run pre-commit install
	@echo "📊 Generating demo data..."
	poetry run python scripts/generate_demo_data.py
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "🚀 Next steps:"
	@echo "  make dev      - Start development server"
	@echo "  make test     - Run test suite"
	@echo ""
	@echo "🔐 For JWT tokens: See README.md authentication section"

# Start development server with auto-reload
dev:
	@echo "🚀 Starting development server..."
	@echo "📖 API Documentation: http://localhost:8000/docs"
	@echo "🔍 Health Check: http://localhost:8000/health"
	@echo "📊 Metrics: http://localhost:8000/metrics"
	@echo ""
	poetry run uvicorn currency_app.main:app --host 0.0.0.0 --port 8000 --reload

# Start production server
run:
	@echo "🚀 Starting production server..."
	poetry run uvicorn currency_app.main:app --host 0.0.0.0 --port 8000

# Build Docker container
build:
	@echo "🐳 Building Docker container..."
	docker build -t currency-api .
	@echo "✅ Container built successfully!"

# Build and run Docker container
docker-run: build
	@echo "🐳 Running Docker container..."
	@echo "📖 API Documentation: http://localhost:8000/docs"
	@echo "🔍 Health Check: http://localhost:8000/health"
	@echo ""
	@echo "Press Ctrl+C to stop the container"
	docker run -p 8000:8000 --rm currency-api

# Run test suite with coverage
test:
	@echo "🧪 Running test suite with coverage..."
	poetry run pytest tests/ -v --cov=currency_app --cov=common --cov-report=term-missing
	@echo "✅ Tests completed!"

# Run quick tests without coverage
test-fast:
	@echo "🏃 Running tests (fast mode)..."
	poetry run pytest tests/ -v
	@echo "✅ Tests completed!"

# Run specific test file
test-file:
	@echo "🧪 Running specific test file..."
	@echo "Usage: make test-file FILE=tests/test_api.py"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: Please specify FILE parameter"; \
		echo "   Example: make test-file FILE=tests/test_api.py"; \
		exit 1; \
	fi
	poetry run pytest $(FILE) -v

# Run code quality checks
quality:
	@echo "🔍 Running code quality checks..."
	@echo "📝 Formatting code..."
	poetry run ruff format currency_app/ common/ tests/
	@echo "🔧 Linting code..."
	poetry run ruff check --fix currency_app/ common/ tests/
	@echo "📋 Type checking..."
	poetry run pyright currency_app/ common/ tests/
	@echo "📄 Generating OpenAPI specification..."
	poetry run python scripts/generate_openapi_spec.py
	@echo "✅ Quality checks completed!"

# Format code only
format:
	@echo "📝 Formatting code..."
	poetry run ruff format currency_app/ common/ tests/
	@echo "✅ Code formatted!"

# Lint code only
lint:
	@echo "🔧 Linting code..."
	poetry run ruff check --fix currency_app/ common/ tests/
	@echo "✅ Code linted!"

# Type check only
typecheck:
	@echo "📋 Type checking..."
	poetry run pyright currency_app/ common/ tests/
	@echo "✅ Type checking completed!"

# Generate demo data
demo-data:
	@echo "📊 Generating demo data..."
	poetry run python scripts/generate_demo_data.py
	@echo "✅ Demo data generated!"


# Generate OpenAPI specification
openapi:
	@echo "📄 Generating OpenAPI specification..."
	poetry run python scripts/generate_openapi_spec.py
	@echo "✅ OpenAPI specification generated!"

# Clean build artifacts and caches
clean:
	@echo "🧹 Cleaning build artifacts and caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .ruff_cache/
	@echo "✅ Cleanup completed!"

# Check service health
health:
	@echo "🔍 Checking service health..."
	@if command -v curl > /dev/null; then \
		curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Service not responding at http://localhost:8000"; \
	else \
		echo "❌ curl not found. Please install curl or check http://localhost:8000/health manually"; \
	fi

# Show service status and URLs
status:
	@echo "📊 Currency API Status"
	@echo ""
	@echo "🌐 Service URLs:"
	@echo "  API Base:      http://localhost:8000"
	@echo "  Documentation: http://localhost:8000/docs"
	@echo "  Health Check:  http://localhost:8000/health"
	@echo "  Metrics:       http://localhost:8000/metrics"
	@echo ""
	@echo "🔍 Quick Health Check:"
	@make health
