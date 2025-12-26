import secrets
import redis
from app.config.settings import REDIS_HOST, REDIS_PORT, SESSION_TTL, EMAIL_VERIFY_TTL_SECONDS, PASS_VERIFY_TTL_SECONDS

import uuid
import json
from datetime import datetime, timedelta
import hashlib

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

def create_session(session_data: dict, email_OTP: bool = False, pass_OTP: bool = False) -> str:
    #Generate secure session ID
    if email_OTP or pass_OTP:
        session_id = secrets.token_urlsafe(32)
        # session_id = hashlib.sha256(session_id.encode()).hexdigest()
        # is there a point to hashing the token
    else:
        session_id = str(uuid.uuid4())

    session_key = f"session:{session_id}"

    #Store session in Redis
    redis_client.hset(session_key, mapping=session_data)

    #Set TTL
    if email_OTP:
        redis_client.expire(session_key, EMAIL_VERIFY_TTL_SECONDS)
    elif pass_OTP:
        redis_client.expire(session_key, PASS_VERIFY_TTL_SECONDS)
    else:
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

def check_rate_limit(key: str, limit: int, period_seconds: int) -> bool:
    #get sessoion from redis
    current = redis_client.get(key)

    #create if not exists, else increment
    if current:
        current = int(current)

        #check if limit exceeded
        if current >= limit:
            return False
        else:
            redis_client.incr(key)
    else:
        redis_client.set(key, 1, ex=period_seconds)
    return True