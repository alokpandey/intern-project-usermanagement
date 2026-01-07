import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock, Mock
from fakeredis import FakeRedis
import os

# Set test environment variables before importing app
os.environ['DB_URL'] = 'sqlite:///:memory:'
os.environ['SENDER_EMAIL'] = 'test@test.com'
os.environ['EMAIL_PASSWORD'] = 'test_password'

# Now import after setting env vars
from main import app
from src.session import get_db
from src.models.DB_models import Base, User
from src.utils.hasher import hash_password

# Use in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_redis():
    """Create a fake Redis instance for testing"""
    fake_redis = FakeRedis()
    yield fake_redis
    fake_redis.flushall()

@pytest.fixture(scope="function", autouse=True)
def mock_email():
    """Mock email sending to prevent actual emails during tests"""
    with patch('src.utils.send_email.send_email_verification', return_value=True):
        with patch('src.utils.send_email.send_password_reset_email', return_value=True):
            yield

@pytest.fixture(scope="function", autouse=True)
def mock_redis_client(test_redis):
    """Mock Redis client to use fake Redis"""
    with patch('src.session.redis_client', test_redis):
        with patch('src.api.router.redis_client', test_redis):
            yield test_redis

@pytest.fixture(scope="function", autouse=True)
def mock_kafka():
    """Mock Kafka producer to prevent actual messages during tests"""
    with patch('src.api.router.send_message', return_value=None):
        yield

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    # Create engine with in-memory SQLite
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Important for in-memory DB
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with overridden database dependency"""
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides after test
    app.dependency_overrides.clear()

@pytest.fixture
def verified_user(test_db):
    """Create a verified test user"""
    user = User(
        username="existinguser",
        email="existing@gmail.com",
        password_hash=hash_password("Test@123"),
        is_verified=True,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def unverified_user(test_db):
    """Create an unverified test user"""
    user = User(
        username="unverified",
        email="unverified@gmail.com",
        password_hash=hash_password("Test@123"),
        is_verified=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user