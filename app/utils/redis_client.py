import secrets
import redis
from app.config.settings import REDIS_HOST, REDIS_PORT, SESSION_TTL, EMAIL_VERIFY_TTL_SECONDS

import uuid
import json
from datetime import datetime, timedelta
import hashlib

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

def create_session(session_data: dict) -> str:
    #Generate secure session ID
    session_id = str(uuid.uuid4())
    session_key = f"session:{session_id}"

    #Store session in Redis
    redis_client.hset(session_key, mapping=session_data)

    #Set TTL
    redis_client.expire(session_key, SESSION_TTL)

    return session_id

def delete_session(session_id: str) -> None:
    session_key = f"session:{session_id}"
    redis_client.delete(session_key)

def get_session(session_id: str) -> dict | None:
    session_key = f"session:{session_id}"

    if not redis_client.exists(session_key):
        return None

    return redis_client.hgetall(session_key)

def create_email_verification_token(user_id: str) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    redis_key = f"email_verify:{token_hash}"

    redis_client.hset(redis_key, mapping={"user_id": user_id, "used": 0})
    redis_client.expire(redis_key, EMAIL_VERIFY_TTL_SECONDS)
    
    return raw_token

def get_email_session(raw_token: str) -> dict | None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session_key = f"email_verify:{token_hash}"

    if not redis_client.exists(session_key):
        return None

    return redis_client.hgetall(session_key)

def use_email_token(raw_token: str) -> None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    redis_key = f"email_verify:{token_hash}"
    redis_client.delete(redis_key)