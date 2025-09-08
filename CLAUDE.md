# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
Currency Conversion API.

## Project Overview

This is a standalone FastAPI-based currency conversion service with comprehensive
observability, authentication, and testing. The service provides:

- **Currency Conversion API**: FastAPI service with 10 major currencies
- **Historical Rate Data**: 30+ days of exchange rate history
- **JWT Authentication**: Secure API access with token validation
- **Prometheus Metrics**: Detailed performance and business metrics
- **OpenTelemetry Tracing**: Distributed tracing for request correlation
- **Comprehensive Testing**: 228+ tests with isolated test databases

## Development Commands

### Quick Start

```bash
poetry install                                    # Install dependencies
poetry run python scripts/generate_demo_data.py  # Generate demo data
poetry run uvicorn currency_app.main:app --reload # Start API server
```

### Docker Workflow

```bash
docker build -t currency-api .                   # Build container
docker run -p 8000:8000 currency-api            # Run container
```

### Testing Commands

```bash
poetry run pytest tests/ -v --cov=currency_app --cov-report=term-missing  # Full test suite
poetry run pytest tests/test_api.py -v                                    # Specific test file
poetry run pytest tests/test_api.py::test_convert_currencies -v          # Single test
poetry run pytest -k "test_convert" -v                                   # Pattern matching
```

### Code Quality

```bash
poetry run ruff format currency_app/ tests/                              # Format code
poetry run ruff check --fix currency_app/ tests/                        # Lint code
poetry run pyright currency_app/ tests/                                 # Type checking
poetry run python scripts/generate_openapi_spec.py                      # Generate API spec
```

## Architecture Overview

### Application Structure

```text
demo_currency_app/
├── currency_app/              # Main FastAPI application
│   ├── main.py               # FastAPI app with lifespan, middleware setup
│   ├── config.py             # Pydantic Settings for environment configuration
│   ├── database.py           # SQLAlchemy engine, session management
│   ├── tracing_config.py     # OpenTelemetry tracing configuration
│   ├── logging_config.py     # Structured logging setup
│   ├── routers/              # FastAPI route handlers
│   │   ├── conversion.py     # Currency conversion endpoints
│   │   ├── rates.py          # Current + historical rates endpoints
│   │   ├── health.py         # Health check endpoints
│   │   └── home.py           # API information endpoint
│   ├── services/             # Business logic layer
│   │   ├── currency_service.py        # Core conversion logic
│   │   └── rates_history_service.py   # Historical data management
│   ├── models/               # Data models
│   │   ├── conversion.py     # Pydantic models for API requests/responses
│   │   └── database.py       # SQLAlchemy ORM models
│   ├── middleware/           # Custom middleware
│   │   ├── auth.py           # JWT authentication middleware
│   │   ├── logging.py        # Request logging middleware
│   │   └── metrics.py        # Prometheus metrics collection
│   └── auth/                 # Authentication utilities
│       └── jwt_auth.py       # JWT token handling
├── tests/                    # Comprehensive test suite
│   ├── databases/            # Isolated test databases
│   ├── test_api.py          # API integration tests
│   ├── test_currency_service.py      # Business logic tests
│   ├── test_database.py              # Database tests
│   └── ...                           # Additional test modules
├── scripts/                  # Utility scripts
│   ├── generate_demo_data.py         # Demo data generation
│   ├── generate_jwt_tokens.py        # Authentication utilities
│   └── generate_openapi_spec.py      # API documentation
└── common/                   # Shared utilities
    └── logging_config.py     # Common logging configuration
```

### Key Architectural Patterns

**Configuration Management**: Uses Pydantic Settings with environment-based
configuration and validation. Settings automatically adapt between production and
development.

**Database Layer**: SQLAlchemy with dependency injection pattern. Database sessions
managed via FastAPI dependencies (`get_db()`). Test isolation uses separate SQLite
databases.

**Service Layer**: Business logic separated into dedicated services with clear
interfaces and comprehensive error handling for currency operations.

**Observability**: Complete observability with Prometheus metrics, OpenTelemetry
tracing, and structured logging. All components instrumented for production monitoring.

**Testing Strategy**: 228+ tests with database isolation. Each test suite uses separate
test databases in `tests/databases/`. Integration tests override database dependencies.

### Database Models

**Key Tables**:

- `conversions`: Currency conversion transactions with full audit trail
- `exchange_rates`: Current exchange rates (10 supported currencies)
- `historical_rates`: Time-series data for 30+ days of rate history

**Important**: USD is the base currency (always 1.0). All rates are relative to USD.

## Available Services and URLs

When running locally:

- **Currency API**: <http://localhost:8000> (FastAPI with interactive docs at /docs)
- **Health Check**: <http://localhost:8000/health> (Service health status)
- **Metrics**: <http://localhost:8000/metrics> (Prometheus metrics)
- **API Info**: <http://localhost:8000/api> (API information and endpoints)

## Test Structure and Patterns

### Test Organization

```text
tests/
├── test_api.py                      # Integration tests for all endpoints
├── test_currency_service.py         # Unit tests for core business logic
├── test_rates_history_service.py    # Historical data service tests
├── test_models.py                   # Pydantic model validation tests
├── test_database.py                 # Database connection tests
├── test_jwt_auth.py                 # Authentication system tests
├── test_metrics_*.py                # Metrics collection tests (4 files)
└── databases/                       # Isolated test databases
    ├── test_currency.db
    ├── test_jwt_auth.db
    └── test_metrics_integration.db
```

### Test Database Isolation

Each test file uses its own test database to prevent interference:

```python
# Pattern used in integration tests
test_db_path = test_db_dir / "test_specific_name.db"
test_engine = create_engine(f"sqlite:///{test_db_path}")
```

**Important**: Always clean up database dependency overrides in test teardown to
prevent test pollution between different test suites.

### Prometheus Metrics Testing

When testing Prometheus Counter metrics, they create both `_total` and `_created` samples:

```python
# Correct pattern for testing Counter metrics
samples = list(counter.collect())[0].samples
total_samples = [s for s in samples if s.name.endswith('_total')]
assert len(total_samples) > 0
```

## Configuration and Environment

**Local Development**: Uses SQLite database (or PostgreSQL), default port 8000
**Docker Deployment**: Uses environment variables, port 8000 exposed

**Key Environment Variables**:

- `DATABASE_URL`: Database connection string (SQLite for local, PostgreSQL for production)
- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `JWT_ALGORITHM`: Algorithm for JWT tokens (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: 60)
- `JAEGER_ENDPOINT`: OpenTelemetry collector endpoint for tracing
- `OTEL_SERVICE_NAME`: Service name for distributed tracing (default: currency-api)

**Database Configuration**:

- **Development**: SQLite (`sqlite:///./currency_demo.db`)
- **Production**: PostgreSQL (`postgresql://user:pass@host:5432/dbname`)
- **Testing**: Isolated SQLite databases in `tests/databases/`

## Development Best Practices

**Type Safety**: Comprehensive type annotations with pyright type checking enabled
**Error Handling**: Custom exceptions (`InvalidCurrencyError`), structured error responses
**Financial Precision**: Uses `Decimal` type with banker's rounding (`ROUND_HALF_EVEN`)
**Request Validation**: Pydantic models validate all inputs with detailed error messages
**Observability**: Request tracing with UUIDs, comprehensive metrics, distributed tracing
**Authentication**: JWT-based authentication with configurable expiration

## Pre-commit Hooks

Configured hooks run automatically before each commit:

- **Ruff**: Code formatting and linting (Python files in `currency_app/`, `tests/`)
- **Pyright**: Type checking (Python files in `currency_app/`, `tests/`)
- **Markdownlint**: Markdown formatting (all `.md` files)
- **OpenAPI Generation**: Automatically generates OpenAPI spec when `currency_app/` files change

Setup: `pre-commit install` after `poetry install` (one-time)

## Code Style Requirements

- Use lowercase built-in types: `list`, `dict`, `set`, `tuple` (not `List`, `Dict`, etc.)
- Keep line length to 100 characters max
- Use Google-style docstrings for all functions and classes
- No trailing whitespace, files must end with newline
- Follow ruff rules configured in pyproject.toml
- Comprehensive type annotations required

## Important Notes for Development

**Database Sessions**: Always use dependency injection via `get_db()` for database access
**Test Isolation**: Each test file uses separate SQLite databases for fast, isolated testing
**Metrics Testing**: Prometheus Counter metrics create both `_total` and `_created` samples
**Tracing**: All components instrumented with OpenTelemetry for request correlation
**Financial Data**: Always use `Decimal` types for currency amounts and exchange rates
**Authentication**: JWT tokens required for protected endpoints, use scripts/generate_jwt_tokens.py

## Currency Service Details

**Supported Currencies**: USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, SEK, NOK
**Base Currency**: USD (always 1.0, other rates relative to USD)
**Rate Updates**: Simulated rate fluctuations with realistic patterns
**Historical Data**: 30+ days of historical rates for trend analysis
**Precision**: All calculations use Python Decimal with banker's rounding

## API Endpoint Patterns

**Conversion**: POST `/api/v1/convert` - Convert between currencies
**Current Rates**: GET `/api/v1/rates` - Get all current exchange rates
**Historical Rates**: GET `/api/v1/rates/history` - Get historical rate data
**Health Check**: GET `/health` - Service health and status
**Metrics**: GET `/metrics` - Prometheus metrics endpoint

## Authentication System

**JWT Implementation**: HS256 algorithm with configurable secret key
**Token Generation**: Use Python to generate development tokens:

```python
from currency_app.auth.jwt_auth import generate_jwt_token
token = generate_jwt_token("acc-demo", "user-demo")
```

**Protected Endpoints**: All `/api/v1/*` endpoints require valid JWT token
**Token Validation**: Automatic middleware validation with detailed error responses
**Expiration**: Configurable token lifetime (default: 60 minutes)
