import json
from unittest.mock import patch

def test_register_success(client):
    payload = {
        "email": "usasder1@example.com",
        "username": "userasd1",
        "password": "passwS#@SDaeord123",
    }

    # with patch("app.utils.kafka_producer.publish_event") as mock_publish:

    response = client.post("/register", json=payload)

    assert response.status_code == 200
    # data = response.json()

    # assert data["email"] == payload["email"]
    # assert data["username"] == payload["username"]
    # mock_publish.assert_called_once()


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "username": "userA",
        "password": "password123",
    }

    client.post("/register", json=payload)

    payload["username"] = "userB"
    response = client.post("/register", json=payload)

    assert response.status_code == 400


def test_register_duplicate_username(client):
    payload = {
        "email": "user2@example.com",
        "username": "dupuser",
        "password": "password123",
    }

    client.post("/register", json=payload)

    payload["email"] = "other@example.com"
    response = client.post("/register", json=payload)

    assert response.status_code == 400
