import pytest
from fastapi.testclient import TestClient


def test_login_success(client, verified_user):
    """Test successful login with verified user"""
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "session_id" in response.cookies


def test_login_unverified_user(client, unverified_user):
    """Test login with unverified account"""
    response = client.post("/api/v1/login", json={
        "email": "unverified@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 401
    assert "Login Failed" in response.json()["message"]


def test_login_wrong_password(client, verified_user):
    """Test login with incorrect password"""
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "WrongPassword@123"
    })
    assert response.status_code == 401
    assert "Login Failed" in response.json()["message"]


def test_login_nonexistent_user(client):
    """Test login with non-existent user"""
    response = client.post("/api/v1/login", json={
        "email": "nonexistent@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 401
    assert "Login Failed" in response.json()["message"]

def test_login_empty_password(client):
    """Test login with empty password"""
    response = client.post("/api/v1/login", json={
        "email": "test@gmail.com",
        "password": ""
    })
    assert response.status_code == 400
    assert "Invalid input" in response.json()["message"]


def test_login_inactive_user(client, test_db):
    """Test login with inactive user account"""
    from src.models.DB_models import User
    from src.utils.hasher import hash_password
    
    # Create inactive user
    inactive_user = User(
        username="inactive",
        email="inactive@gmail.com",
        password_hash=hash_password("Test@123"),
        is_verified=True,
        is_active=False  # Inactive account
    )
    test_db.add(inactive_user)
    test_db.commit()
    
    response = client.post("/api/v1/login", json={
        "email": "inactive@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 401
    assert "Login Failed" in response.json()["message"]


def test_login_account_locking_after_3_attempts(client, verified_user, test_redis):
    """Test account gets locked after 3 failed login attempts"""
    
    # Make 3 failed login attempts
    for i in range(3):
        response = client.post("/api/v1/login", json={
            "email": "existing@gmail.com",
            "password": "WrongPassword@123"
        })
        assert response.status_code == 401
    
    # Check if user is locked in Redis
    lock_key = f"lock_user:{verified_user.id}"
    assert test_redis.exists(lock_key) == 1
    
    # 4th attempt should fail even with correct password
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"  # Correct password
    })
    assert response.status_code == 401
    assert "locked" in response.json()["message"].lower()


def test_login_attempts_counter_increments(client, verified_user, test_redis):
    """Test that failed login attempts are counted in Redis"""
    
    # First failed attempt
    client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "WrongPassword@123"
    })
    
    attempts_key = f"login_attempts:{verified_user.id}"
    attempts = test_redis.get(attempts_key)
    assert attempts is not None
    assert int(attempts) == 1
    
    # Second failed attempt
    client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "WrongPassword@123"
    })
    
    attempts = test_redis.get(attempts_key)
    assert int(attempts) == 2


def test_login_attempts_reset_on_success(client, verified_user, test_redis):
    """Test that login attempts counter is reset after successful login"""
    
    # Make 2 failed attempts
    for i in range(2):
        client.post("/api/v1/login", json={
            "email": "existing@gmail.com",
            "password": "WrongPassword@123"
        })
    
    attempts_key = f"login_attempts:{verified_user.id}"
    assert test_redis.exists(attempts_key) == 1
    
    # Successful login
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 200
    
    # Attempts counter should be deleted
    assert test_redis.exists(attempts_key) == 0


def test_login_session_created_in_redis(client, verified_user, test_redis):
    """Test that session is created in Redis after successful login"""
    
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"
    })
    
    assert response.status_code == 200
    session_id = response.cookies.get("session_id")
    assert session_id is not None
    
    # Check session exists in Redis
    session_key = f"session:{session_id}"
    assert test_redis.exists(session_key) == 1
    
    # Check session contains user ID
    user_id = test_redis.get(session_key)
    assert user_id is not None
    assert int(user_id) == verified_user.id


def test_login_session_cookie_properties(client, verified_user):
    """Test that session cookie has correct security properties"""
    
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"
    })
    
    assert response.status_code == 200
    
    # Check cookie exists
    assert "session_id" in response.cookies
    
    # Note: TestClient doesn't expose all cookie properties
    # In production, verify: httponly=True, secure=True (for HTTPS), samesite="lax"


def test_login_locked_user_cannot_login(client, verified_user, test_redis):
    """Test that a locked user cannot login even with correct credentials"""
    
    # Manually lock the user
    lock_key = f"lock_user:{verified_user.id}"
    test_redis.setex(lock_key, 120, str(verified_user.id))
    
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "Test@123"
    })
    
    assert response.status_code == 401
    assert "locked" in response.json()["message"].lower()


def test_login_case_sensitive_password(client, verified_user):
    """Test that password is case-sensitive"""
    
    response = client.post("/api/v1/login", json={
        "email": "existing@gmail.com",
        "password": "test@123"  # lowercase 't'
    })
    
    assert response.status_code == 401
    assert "Login Failed" in response.json()["message"]


def test_login_missing_fields(client):
    """Test login with missing required fields"""
    
    # Missing password
    response = client.post("/api/v1/login", json={
        "email": "test@gmail.com"
    })
    assert response.status_code == 422  # FastAPI validation error
    
    # Missing email
    response = client.post("/api/v1/login", json={
        "password": "Test@123"
    })
    assert response.status_code == 422  # FastAPI validation error