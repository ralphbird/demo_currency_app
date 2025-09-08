# Currency Conversion API 💰

A production-ready FastAPI-based currency conversion service with comprehensive
observability, authentication, and testing.

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Build and run the API
docker build -t currency-api .
docker run -p 8000:8000 currency-api

# API available at: http://localhost:8000
# Documentation: http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
poetry install

# Generate demo data
poetry run python scripts/generate_demo_data.py

# Start the API server
poetry run uvicorn currency_app.main:app --reload

# API available at: http://localhost:8000
```

## 📋 Features

### Core Functionality

- **10 Major Currencies**: USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, SEK, NOK
- **Real-time Conversion**: High-precision decimal arithmetic with banker's rounding
- **Historical Rates**: 30+ days of exchange rate history with trend analysis
- **Rate Validation**: Comprehensive input validation and error handling

### Production Features

- **JWT Authentication**: Secure API access with token-based auth
- **Prometheus Metrics**: Detailed performance and business metrics
- **OpenTelemetry Tracing**: Distributed tracing for request correlation
- **Health Checks**: Comprehensive health monitoring endpoints
- **Database Persistence**: SQLAlchemy with PostgreSQL/SQLite support

### Developer Experience

- **228+ Tests**: Comprehensive test coverage with isolated test databases
- **OpenAPI Docs**: Interactive API documentation at `/docs`
- **Code Quality**: Ruff formatting, linting, and Pyright type checking
- **Pre-commit Hooks**: Automated code quality checks

## 🌐 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/convert` | POST | Convert between currencies |
| `/api/v1/rates` | GET | Get current exchange rates |
| `/api/v1/rates/history` | GET | Get historical exchange rates |
| `/health` | GET | Health check status |
| `/metrics` | GET | Prometheus metrics |

### Example Usage

```bash
# Get current rates (no auth required)
curl "http://localhost:8000/api/v1/rates"

# Get historical rates for EUR (no auth required)
curl "http://localhost:8000/api/v1/rates/history?currency=EUR&days=7"

# Convert 100 USD to EUR (requires JWT token)
curl -X POST "http://localhost:8000/api/v1/convert" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "from_currency": "USD",
    "to_currency": "EUR",
    "amount": 100.00
  }'
```

### 🔐 Authentication

The `/api/v1/convert` endpoint requires JWT authentication. Generate a token using Python:

```python
# Generate a JWT token for testing
from currency_app.auth.jwt_auth import generate_jwt_token

# Create a token (no expiration for development)
token = generate_jwt_token(
    account_id="acc-test-001",
    user_id="user-test-001"
)
print(f"Authorization: Bearer {token}")
```

Or use the interactive Python shell:

```bash
# Start Python shell with currency_app available
poetry run python

>>> from currency_app.auth.jwt_auth import generate_jwt_token
>>> token = generate_jwt_token("acc-demo", "user-demo")
>>> print(f"Bearer {token}")
```

## 🏗️ Architecture

### Directory Structure

```text
demo_currency_app/
├── currency_app/           # Main FastAPI application
│   ├── routers/           # API endpoint handlers
│   ├── services/          # Business logic layer
│   ├── models/            # Pydantic and SQLAlchemy models
│   ├── middleware/        # Custom middleware (auth, logging, metrics)
│   └── auth/              # JWT authentication
├── tests/                 # Comprehensive test suite
├── scripts/               # Utility scripts
├── common/                # Shared utilities
└── docs/                  # Documentation
```

### Core Components

- **FastAPI Application**: High-performance async web framework
- **SQLAlchemy ORM**: Database abstraction with migration support
- **Pydantic Models**: Request/response validation and serialization
- **JWT Authentication**: Secure API access with configurable expiration
- **Prometheus Integration**: Detailed metrics collection
- **OpenTelemetry**: Distributed tracing and observability

## 🧪 Testing

### Run Test Suite

```bash
# Full test suite with coverage
poetry run pytest tests/ -v --cov=currency_app --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_api.py -v

# Run specific test
poetry run pytest tests/test_api.py::test_convert_currencies -v

# Run tests matching pattern
poetry run pytest -k "test_convert" -v
```

### Test Coverage

- **API Integration Tests**: Full endpoint testing with authentication
- **Service Layer Tests**: Business logic validation and error handling
- **Database Tests**: SQLAlchemy model and migration testing
- **Metrics Tests**: Prometheus metrics collection validation
- **Authentication Tests**: JWT token validation and security

### Test Isolation

Each test file uses isolated SQLite databases in `tests/databases/` to prevent test
interference and ensure fast, reliable testing.

## 🛠️ Development

### Code Quality

```bash
# Format code
poetry run ruff format currency_app/ tests/

# Lint code
poetry run ruff check --fix currency_app/ tests/

# Type checking
poetry run pyright currency_app/ tests/

# Generate OpenAPI specification
poetry run python scripts/generate_openapi_spec.py
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (one-time)
poetry install
pre-commit install

# Hooks run automatically on commit:
# - Code formatting (Ruff)
# - Linting (Ruff)
# - Type checking (Pyright)
# - OpenAPI spec generation
# - Markdown formatting
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=sqlite:///./currency_demo.db  # Local SQLite
# DATABASE_URL=postgresql://user:pass@localhost:5432/currency_db  # PostgreSQL

# API Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Tracing (Optional)
JAEGER_ENDPOINT=http://localhost:14268/api/traces
OTEL_SERVICE_NAME=currency-api
```

## 📊 Monitoring & Observability

### Prometheus Metrics

Available at `/metrics` endpoint:

- **Business Metrics**: Conversion counts, rate lookups, currency pair popularity
- **Performance Metrics**: Response times, database query duration
- **System Metrics**: HTTP request counts, error rates, authentication metrics

### OpenTelemetry Tracing

- **Request Tracing**: End-to-end request correlation with trace IDs
- **Database Tracing**: SQLAlchemy query instrumentation
- **External Request Tracing**: HTTP client request monitoring
- **Custom Spans**: Business logic instrumentation with rich context

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Response includes:
# - Service status
# - Database connectivity
# - Available currencies
# - System uptime
```

## 🔒 Security

### Authentication

- **JWT Tokens**: HS256 algorithm with configurable expiration
- **Token Validation**: Automatic token verification on protected endpoints
- **Rate Limiting**: Built-in protection against abuse (configurable)

### Data Protection

- **Input Validation**: Comprehensive Pydantic model validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Error Handling**: Secure error responses without information leakage

## 🚢 Deployment

### Docker Deployment

```bash
# Single-service deployment
docker build -t currency-api .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/currency_db \
  -e JWT_SECRET_KEY=your-secret-key \
  currency-api
```

### Production Considerations

- **Database**: Use PostgreSQL for production (SQLite for development)
- **Environment Variables**: Configure via `.env` file or container environment
- **Health Checks**: Integrate with container orchestration health checks
- **Metrics Collection**: Connect Prometheus to `/metrics` endpoint
- **Tracing**: Configure Jaeger or other OpenTelemetry-compatible backends

## 📈 Performance

### Benchmarks

- **Throughput**: 1000+ requests/second (single instance)
- **Latency**: Sub-10ms response times for cached rates
- **Concurrency**: Full async/await support for high concurrency
- **Database**: Optimized queries with connection pooling

### Optimization

- **Database Indexes**: Optimized for common query patterns
- **Connection Pooling**: Configured for production workloads
- **Caching**: In-memory rate caching for frequently accessed pairs
- **Async Operations**: Non-blocking I/O for maximum throughput

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes with comprehensive tests
4. Run quality checks: `poetry run ruff check && poetry run pyright`
5. Submit pull request with detailed description

### Code Standards

- **Type Annotations**: All functions must have type hints
- **Docstrings**: Google-style docstrings for all public functions
- **Test Coverage**: New features require comprehensive tests
- **Code Quality**: Must pass Ruff linting and Pyright type checking

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **API Documentation**: <http://localhost:8000/docs> (when running)
- **Issues**: Report bugs and feature requests via GitHub issues
- **Health Check**: <http://localhost:8000/health> for service status
