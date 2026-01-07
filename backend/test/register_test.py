import pytest
from fastapi.testclient import TestClient

def test_register_invalid_email(client):
    """Test registration with non-Gmail email"""
    response = client.post("/api/v1/register", json={
        "username": "testuser",
        "email": "test@yahoo.com",
        "password": "Test@123"
    })
    assert response.status_code == 400

def test_register_weak_password(client):
    """Test registration with weak password"""
    response = client.post("/api/v1/register", json={
        "username": "testuser",
        "email": "test@gmail.com",
        "password": "weak"
    })
    assert response.status_code == 406

def test_register_duplicate_user(client, verified_user):
    """Test registration with existing email"""
    response = client.post("/api/v1/register", json={
        "username": "newuser",
        "email": verified_user.email,  # Use existing user's email
        "password": "Test@123"
    })
    assert response.status_code == 409

def test_register_invalid_username(client):
    """Test registration with username containing numbers"""
    response = client.post("/api/v1/register", json={
        "username": "testuser123",  # Contains numbers
        "email": "test@gmail.com",
        "password": "Test@123"
    })
    assert response.status_code == 400

def test_register_empty_fields(client):
    """Test registration with empty fields"""
    response = client.post("/api/v1/register", json={
        "username": "",
        "email": "",
        "password": ""
    })
    assert response.status_code == 422

