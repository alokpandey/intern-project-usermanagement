from app.db.models import User

def test_user_model_defaults():
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
    )

    assert user.email == "test@example.com"
