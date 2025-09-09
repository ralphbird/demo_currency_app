.PHONY: help install setup dev run build up down logs rebuild test quality clean docker-clean

# Default target - shows available commands
help:
	@echo "💰 Currency Conversion API - Development Commands"
	@echo ""
	@echo "📋 Available Commands:"
	@echo "  make install  - Install dependencies with Poetry"
	@echo "  make setup    - Complete setup (install + pre-commit + demo data)"
	@echo "  make dev      - Start development server with auto-reload"
	@echo "  make run      - Start production server"
	@echo "  make up       - Start all services with full monitoring stack (Docker)"
	@echo "  make down     - Stop all Docker services"
	@echo "  make logs     - View Docker service logs"
	@echo "  make rebuild  - Rebuild and restart all Docker services"
	@echo "  make build    - Build Docker containers only"
	@echo "  make test     - Run test suite with coverage"
	@echo "  make quality  - Run code quality checks (format, lint, type-check)"
	@echo "  make clean    - Clean build artifacts and caches"
	@echo "  make docker-clean - Clean all Docker resources"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup    - Set up everything for development"
	@echo "  make dev      - Start development server"
	@echo "  make up       - Start with full monitoring stack (PostgreSQL + Grafana)"
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

# Build Docker containers
build:
	@echo "🐳 Building Docker containers..."
	docker-compose build
	@echo "✅ Containers built successfully!"

# Start all services with full monitoring stack
up:
	@echo "🐳 Starting Currency API with full monitoring stack..."
	docker-compose up -d
	@echo "✅ All services started!"
	@echo ""
	@echo "🚀 Available at:"
	@echo "   💰 API: http://localhost:8000"
	@echo "   📈 Prometheus: http://localhost:9090"
	@echo "   📉 Grafana: http://localhost:3000 (admin/admin)"
	@echo "   🔍 Jaeger: http://localhost:16686"
	@echo "   🗄️  PostgreSQL: localhost:5432"
	@echo ""
	@echo "Type 'make down' to stop all services"

# Stop all services
down:
	@echo "🐳 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped!"

# View service logs
logs:
	@echo "📊 Viewing service logs (Ctrl+C to exit)..."
	docker-compose logs -f

# Rebuild and restart all services
rebuild:
	@echo "🔄 Rebuilding and restarting all services..."
	docker-compose down
	docker-compose build
	docker-compose up -d
	@echo "✅ Services rebuilt and restarted!"
	@echo ""
	@echo "🚀 Available at:"
	@echo "   💰 API: http://localhost:8000"
	@echo "   📈 Prometheus: http://localhost:9090"
	@echo "   📉 Grafana: http://localhost:3000 (admin/admin)"
	@echo "   🔍 Jaeger: http://localhost:16686"

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

# Run code quality checks
quality:
	@echo "🔍 Running code quality checks..."
	@echo "📝 Formatting code..."
	poetry run ruff format currency_app/ common/ tests/
	@echo "🔧 Linting code..."
	poetry run ruff check --fix currency_app/ common/ tests/
	@echo "📋 Type checking..."
	poetry run pyright currency_app/ common/ tests/
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

# Clean all Docker resources
docker-clean:
	@echo "🧹 Cleaning all Docker resources..."
	docker-compose down -v --rmi local --remove-orphans
	docker system prune -f
	@echo "✅ Docker cleanup completed!"

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
