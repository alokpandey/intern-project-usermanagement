from app.utils.token_utils import validate_email, validate_password, get_hashed_password, verify_password
from fastapi import FastAPI, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
import datetime
from app.config.settings import SESSION_TTL

from app.db.database import get_db, init_db
from app.db.models import Base, User
from app.utils.kafka_producer import publish_event
from app.db.schemas import UserCreate, UserLoginRequest
from app.utils.redis_client import (create_email_verification_token, create_session, 
                                    get_email_session, get_session, delete_session, use_email_token)


from sqlalchemy.exc import OperationalError
from datetime import datetime, timezone

app = FastAPI()
@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email or username already registered")

    is_valid_email = validate_email(user.email)
    if not is_valid_email:
        # update_request_info(redis_client, redis_key, "failed")
        pass
    
    is_valid_password = validate_password(user.password)
    if not is_valid_password:
        # update_request_info(redis_client, redis_key, "failed")
        pass

    encrypted_password = get_hashed_password(user.password)

    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=encrypted_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    #send this token to the email
    token = create_email_verification_token(new_user.id)
    
    publish_event(
        "user_registered",
        {
            "user_id": new_user.id,
            "email": new_user.email,
            "verified": False,
        }
    )

    return {"message": "User registered successfully", "token": token}

@app.post("/login")
def login(logIn: UserLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    
    client_host = request.client.host

    if logIn.email is None and logIn.username is None:
        raise HTTPException(status_code=400, detail="Email or username required")
    
    user = db.query(User).filter(
        (User.email == logIn.email) | (User.username == logIn.username)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_verified == False:
        raise HTTPException(status_code=403, detail="Email not verified")

    if verify_password(logIn.password, user.hashed_password) == False:
        user.failed_login_attempts += 1
        raise HTTPException(status_code=401, detail="Invalid Password") #should i do password or credentials
    
    user.failed_login_attempts = 0
    
    session = create_session(
        {
            "user_id": user.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": client_host
        }
            #"user_agent": 
    )

    response.set_cookie(
        key="session_id",
        value=session,
        httponly=True,
        secure=True,          
        samesite="lax",       
        max_age=SESSION_TTL,
        path="/",
    )

    publish_event(
        "user_log_in_success",
        {
            "user_id": user.id,
            "success": "success",
            "email": user.email,
            "ip": client_host,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    return {"message": "Login successful", "session": session, "user": user.username, "timestamp": datetime.now(timezone.utc).isoformat()}
    
@app.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")

    if not session_id:
        response.delete_cookie(key="session_id", path="/")
        return {"message": "User is already logged out"}

    session_data = get_session(session_id)

    if session_data:
        delete_session(session_id)

        publish_event(
            "user_logout",
            {
                "user_id": session_data.get("user_id"),
                "ip": request.client.host,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    response.delete_cookie(
        key="session_id",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"message": "Logged out"}

@app.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email_session = get_email_session(token)
    if not email_session:   
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if email_session.get("used") == "1":
        raise HTTPException(status_code=400, detail="Token already used")
    
    user = db.query(User).filter(User.id == email_session["user_id"]).first()

    # if not user:
    #     raise HTTPException(status_code=400, detail="User not found")
    
    user.is_verified = True
    db.commit()

    # Invalidate token (Redis)
    use_email_token(token)
    
    publish_event(
        "email_verified",
        {
            "user_id": user.id,
            "email": user.email
        }
    )
    return {"message": "Email verified successfully"}

@app.get("/health")
def health():
    return {"status": "ok"}
