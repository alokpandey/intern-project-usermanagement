from app.utils.token_utils import validate_email, validate_password, get_hashed_password, verify_password
from fastapi import FastAPI, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
import datetime
from app.config.settings import (EMAIL_HOST, EMAIL_PORT, SESSION_TTL, FRONT_END_URL, EMAIL_FROM,
                                 RATE_LIMIT_RESET_PASSWORD, RATE_LIMIT_PERIOD_SECONDS,
                                 RATE_LIMIT_LOGIN_ATTEMPTS, RATE_LIMIT_LOGIN_PERIOD_SECONDS)
import smtplib
from email.message import EmailMessage

from app.db.database import get_db, init_db
from app.db.models import Base, User
from app.utils.kafka_producer import publish_event
from app.db.schemas import UserCreate, UserLoginRequest
from app.utils.redis_client import (create_session,  get_session, delete_session, check_rate_limit)

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

    validate_email(user.email)
    validate_password(user.password)
    
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_hashed_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_session(
        {
            "user_id": new_user.id,
            "username": new_user.username,
            "used": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, email_OTP=True
    )

    reset_link = f"{FRONT_END_URL}/verify-email?token={token}"
    email_body = f"Click the following link to verify your email: {reset_link}"
    send_email(to_email=user.email, subject="Verify Email", body=email_body)
    
    publish_event(
        {
            "username": new_user.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "successful_register"
        }
    )

    return {"message": "User registered successfully"}

@app.post("/login")
def login(logIn: UserLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    if logIn.email is None and logIn.username is None:
        
        raise HTTPException(status_code=400, detail="Email or username required")
    
    session_id = request.cookies.get("session_id")

    if session_id:
        return {"message": "User already logged in"}

    client_host = request.client.host
    # ideally ip might be better, but for testing I will user email/username
    # rate_limit_key = f"log_in_attempts:{client_host}" 
    rate_limit_key = logIn.email if logIn.email else logIn.username

    if not check_rate_limit(rate_limit_key, RATE_LIMIT_LOGIN_ATTEMPTS, RATE_LIMIT_LOGIN_PERIOD_SECONDS):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    user = db.query(User).filter(
        (User.email == logIn.email) | (User.username == logIn.username)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_verified == False:
        publish_event({"operation": "failed_login", "username": user.username,"timestamp": datetime.now(timezone.utc).isoformat(), "reason": "email_not_verified"})
        raise HTTPException(status_code=403, detail="Email not verified")

    if verify_password(logIn.password, user.hashed_password) == False:
        publish_event({"operation": "failed_login", "username": user.username,"timestamp": datetime.now(timezone.utc).isoformat(), "reason": "invalid_password"})
        raise HTTPException(status_code=401, detail="Invalid Password") #should i do password or credentials
    
    session = create_session(
        {
            "user_id": user.id,
            "username": user.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": client_host
        }
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

    publish_event({"operation": "successful_login", "username": user.username,"timestamp": datetime.now(timezone.utc).isoformat()})
    
    return {"message": "Login successful", "user": user.username}
    
@app.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")

    if not session_id:
        response.delete_cookie(key="session_id", path="/")
        return {"message": "User is already logged out"}

    session_data = get_session(session_id)

    if session_data:
        delete_session(session_id)

        publish_event({"operation": "successful_logout", "username": session_data.get("username"),"timestamp": datetime.now(timezone.utc).isoformat()})

    response.delete_cookie(
        key="session_id",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"message": "Logged out"}

#get helps me just click the link, but post is more accurate for the change of user verification status
#also what if user just never clicks the link, should I have a way to resend?
@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email_session = get_session(token)
    if not email_session:   
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if email_session.get("used") == "1":
        raise HTTPException(status_code=400, detail="Token already used")
    
    user = db.query(User).filter(User.id == email_session["user_id"]).first()

    # if not user:
    #     raise HTTPException(status_code=400, detail="User not found")
    
    user.is_verified = True
    db.commit()

    delete_session(token)

    publish_event({"operation": "email_verified", "username": email_session.get("username"),"timestamp": datetime.now(timezone.utc).isoformat()})

    return {"message": "Email verified successfully"}

@app.post("/password-reset/request")
def request_password_reset(email: str, db: Session = Depends(get_db)):
    rate_limit_key = f"pwd_reset:{email}"

    if not check_rate_limit(rate_limit_key, RATE_LIMIT_RESET_PASSWORD, RATE_LIMIT_PERIOD_SECONDS):
        raise HTTPException(status_code=429, detail="Too many password reset requests. Try again later.")

    user = db.query(User).filter(User.email == email).first()

    if user:
        token = create_session(
            {
                "user_id": user.id,
                "username": user.username,
                "used": 0
            }, pass_OTP=True
        )

        reset_link = f"{FRONT_END_URL}/password-reset?token={token}&"
        reset_link = f"{FRONT_END_URL}/password-reset?token={token}&new_password=aSs2dfj83w@4jw03j" 
        email_body = f"Add your password to the link above and click it to reset: {reset_link}"
        send_email(to_email=user.email, subject="Password Reset Request", body=email_body)

        publish_event({"operation": "password_reset_requested", "username": user.username,"timestamp": datetime.now(timezone.utc).isoformat()})

        
    return {"message": "If an account exists, a password reset email has been sent."}

#get helps me just click the link, but post is more accurate for the change of user verification status
@app.get("/password-reset")
def password_reset(token: str, new_password: str, db: Session = Depends(get_db)):
    
    #doing this before lets me keep the token still reusable if the password is invalid
    validate_password(new_password)
    
    session = get_session(token)
    if not session:   
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if session.get("used") == "1":
        raise HTTPException(status_code=400, detail="Token already used")
    
    user = db.query(User).filter(User.id == session["user_id"]).first()

    # if not user:
    #     raise HTTPException(status_code=400, detail="User not found")
    
    user.hashed_password = get_hashed_password(new_password)
    db.commit()

    delete_session(token)

    publish_event({"operation": "successful_password_reset", "username": user.username,"timestamp": datetime.now(timezone.utc).isoformat()})

    return {"message": "Password reset successfully"}

def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.send_message(msg)

    # with smtplib.SMTP("mailhog", 1025) as server:
    #     server.send_message(msg)
