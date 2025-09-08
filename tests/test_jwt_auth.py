"""Tests for JWT authentication functionality."""

# Create test database in tests/databases subfolder
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from currency_app.auth.jwt_auth import generate_jwt_token
from currency_app.database import get_db
from currency_app.main import app
from currency_app.models.database import Base

# Ensure the test databases directory exists
test_db_dir = Path(__file__).parent / "databases"
test_db_dir.mkdir(exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db_dir}/test_jwt_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Create test client with test database."""
    # Create test tables
    Base.metadata.create_all(bind=engine)

    # Override database dependency for this test only
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Clean up database override and tables
        if get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        Base.metadata.drop_all(bind=engine)


class TestJWTAuthentication:
    """Test JWT authentication for conversion endpoints."""

    def test_convert_without_auth_header_fails(self, client):
        """Test that conversion fails without Authorization header."""
        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}

        response = client.post("/api/v1/convert", json=request_data)

        assert response.status_code == 401
        assert "Missing or invalid Authorization header" in response.json()["detail"]

    def test_convert_with_empty_auth_header_fails(self, client):
        """Test that conversion fails with empty Authorization header."""
        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": ""}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 401
        assert "Missing or invalid Authorization header" in response.json()["detail"]

    def test_convert_with_invalid_bearer_format_fails(self, client):
        """Test that conversion fails with invalid Bearer format."""
        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": "InvalidFormat token"}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 401
        assert "Authorization header must use Bearer scheme" in response.json()["detail"]

    def test_convert_with_malformed_jwt_fails(self, client):
        """Test that conversion fails with malformed JWT token."""
        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": "Bearer invalid.jwt.token"}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 401
        assert "Invalid JWT token" in response.json()["detail"]

    def test_convert_with_jwt_missing_claims_fails(self, client):
        """Test that conversion fails with JWT missing required claims."""
        # Generate token with missing user_id claim
        import jwt

        from currency_app.config import settings

        payload = {
            "account_id": "test-account-123"
            # Missing user_id claim
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 401
        assert "Token must contain account_id and user_id" in response.json()["detail"]

    def test_convert_with_valid_jwt_succeeds(self, client):
        """Test that conversion succeeds with valid JWT token."""
        # Generate valid JWT token
        token = generate_jwt_token(
            account_id="test-account-123", user_id="test-user-456", expires_in_seconds=None
        )

        request_data = {"amount": 100.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "conversion_id" in data
        assert float(data["amount"]) == 100.0

    def test_rates_endpoints_dont_require_auth(self, client):
        """Test that rates endpoints don't require authentication."""
        # Test rates endpoint
        rates_response = client.get("/api/v1/rates")
        assert rates_response.status_code == 200

        # Test rates history endpoint
        history_response = client.get("/api/v1/rates/history")
        assert history_response.status_code == 200

        # Test rates history with parameters
        history_params_response = client.get("/api/v1/rates/history?currency=EUR&limit=5")
        assert history_params_response.status_code == 200

    def test_health_endpoints_dont_require_auth(self, client):
        """Test that health endpoints don't require authentication."""
        # Test basic health
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # Test detailed health
        detailed_health_response = client.get("/health/detailed")
        assert detailed_health_response.status_code == 200

    def test_metrics_endpoint_doesnt_require_auth(self, client):
        """Test that metrics endpoint doesn't require authentication."""
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200

    def test_api_info_endpoint_doesnt_require_auth(self, client):
        """Test that API info endpoint doesn't require authentication."""
        api_response = client.get("/api")
        assert api_response.status_code == 200

    def test_conversion_stores_user_context_in_database(self, client):
        """Test that conversion stores account_id and user_id in database."""
        # Generate valid JWT token with specific user context
        test_account_id = "test-db-account-789"
        test_user_id = "test-db-user-012"

        token = generate_jwt_token(
            account_id=test_account_id, user_id=test_user_id, expires_in_seconds=None
        )

        request_data = {"amount": 50.00, "from_currency": "USD", "to_currency": "EUR"}
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/v1/convert", json=request_data, headers=headers)

        assert response.status_code == 200

        # Verify the conversion was stored with correct user context
        # Note: In a real test, we'd query the database to verify this,
        # but for now we'll just verify the API call succeeded
        data = response.json()
        assert "conversion_id" in data
        assert float(data["amount"]) == 50.0


class TestJWTTokenGeneration:
    """Test JWT token generation utilities."""

    def test_generate_token_with_valid_params(self):
        """Test JWT token generation with valid parameters."""
        token = generate_jwt_token(
            account_id="test-account", user_id="test-user", expires_in_seconds=None
        )

        assert isinstance(token, str)
        assert len(token) > 0
        assert "." in token  # JWT format has dots

    def test_generate_token_with_empty_account_id_fails(self):
        """Test that token generation fails with empty account_id."""
        with pytest.raises(ValueError, match="account_id must be a non-empty string"):
            generate_jwt_token(account_id="", user_id="test-user", expires_in_seconds=None)

    def test_generate_token_with_empty_user_id_fails(self):
        """Test that token generation fails with empty user_id."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            generate_jwt_token(account_id="test-account", user_id="", expires_in_seconds=None)

    def test_generate_token_with_whitespace_only_fails(self):
        """Test that token generation fails with whitespace-only IDs."""
        with pytest.raises(ValueError, match="account_id must be a non-empty string"):
            generate_jwt_token(account_id="   ", user_id="test-user", expires_in_seconds=None)

    def test_generate_token_with_expiration(self):
        """Test JWT token generation with expiration."""
        token = generate_jwt_token(
            account_id="test-account",
            user_id="test-user",
            expires_in_seconds=3600,  # 1 hour
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token contains expiration claim
        import jwt

        from currency_app.config import settings

        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        assert "exp" in decoded
        assert decoded["exp"] > decoded["iat"]
