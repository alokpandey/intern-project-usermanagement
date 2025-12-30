from fastapi import APIRouter, Depends,  HTTPException, status
from ..models.api_models import UserData, SuccessResponse, ErrorResponse, VerifyOTP, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from ..models.DB_models import User
from ..session import get_db
import logging
from sqlalchemy.orm import Session
from src.utils.hasher import hash_password, check_password
from fastapi.responses import JSONResponse
from fastapi import Request
from src.utils.send_email import send_email_verification, send_password_reset_email
from ..session import redis_client
import secrets
from ..kafka_pc.kafka_producer import send_message
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.utils.password_validator import validate_password


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

router = APIRouter()

special_chars = "#@!%&*"

@router.post("/register")
async def register(user : UserData, db: Session = Depends(get_db)):
    if not user.username  or not user.email or not user.password or user.email.endswith("@gmail.com") == False or not user.username.isalpha():
        logger.error("Invalid input")
        response = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=response.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)    

    elif not validate_password(user.password):
        logger.error("PASSWORD NOT STRONG!!!")
        response = ErrorResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, message=f""" * Password should be minimum 8 characters.
                                * Password should contain atleast one special character.  
                                * Password should contaian One digit, and one uppercase letter.""")
        return JSONResponse(content=response.model_dump(), status_code=status.HTTP_406_NOT_ACCEPTABLE)
    
    
    else:   
        try:
            password_hash =  hash_password(user.password)

            new_user = User(
            username=user.username,
            email=user.email,
            password_hash=password_hash,
            is_verified=False
        )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            audit_data = {"username": new_user.username,"operation": "Register","timestamp": str(new_user.created_at)}
            logger.info(f"send message to kafka: {audit_data}")
            send_message(audit_data)
            email_status=send_email_verification(new_user.email, new_user.id)
            if email_status == False:
                logger.error("Error sending email")
                response = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error sending email")
                return JSONResponse(content=response.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error: {e}")
            response = ErrorResponse(
                status_code=status.HTTP_409_CONFLICT,
                message="User already exists"
            )
            return JSONResponse(content=response.model_dump(), status_code=409)

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            response = ErrorResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error"
            )
            return JSONResponse(content=response.model_dump(), status_code=500)

        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error: {e}")
            response = ErrorResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Registration failed"
            )
            return JSONResponse(content=response.model_dump(), status_code=500)
    response = SuccessResponse(message="User created successfully", user_id=new_user.id, verification_required=True)
    return JSONResponse(content=response.model_dump(), status_code=status.HTTP_201_CREATED)


@router.post("/verify/otp")
async def login(data : VerifyOTP, db: Session = Depends(get_db)):
    if data.user_id == "" or data.otp == "":
        logger.error("Invalid input")
        response = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=response.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            lock_key = f"lock_user:{data.user_id}"
            rate_limit_key = f"rate_limit:{data.user_id}"
            otp_key = f"otp_{data.user_id}"

            if redis_client.exists(lock_key):
                logger.error("User temporarily locked")
                response = ErrorResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    message="Too many attempts. Try again later."
                )
                return JSONResponse(content=response.model_dump(), status_code=429)
            attempts = redis_client.get(rate_limit_key)
            if attempts and int(attempts) >= 3:
                redis_client.setex(lock_key, 120, "locked")
                redis_client.delete(rate_limit_key)
                logger.error("Too many attempts")
                response = ErrorResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    message="Too many attempts"
                )
                return JSONResponse(content=response.model_dump(), status_code=429)
            otp = redis_client.get(otp_key)

            if otp is None:
                logger.error("OTP expired")
                response = ErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="OTP expired"
                )
                return JSONResponse(content=response.model_dump(), status_code=400)
            if otp.decode() == str(data.otp):
                redis_client.delete(otp_key)
                redis_client.delete(rate_limit_key)
                updated = db.query(User).filter(User.id == data.user_id).update({"is_verified": True})
                db.commit()
                if not updated:
                    logger.error("User not found")
                    response = ErrorResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="User not found"
                    )
                    return JSONResponse(content=response.model_dump(), status_code=404)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "OTP verified successfully"})
            attempts = redis_client.incr(rate_limit_key)
            if attempts == 1:
                redis_client.expire(rate_limit_key, 300)

            logger.error("Invalid OTP")
            response = ErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid OTP"
            )
            return JSONResponse(content=response.model_dump(), status_code=400)
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            response = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error verifying OTP")
            return JSONResponse(content=response.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
async def login(data : UserLogin, db: Session = Depends(get_db)):
    if data.email == "" or data.password == "":
        logger.error("Invalid input")
        response = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=response.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
    else:
        try: 
            user = db.query(User).filter(User.email == data.email).first()
            if not user or not user.is_verified or not user.is_active:
                logger.error("User does not exist")
                response = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Login Failed")
                return JSONResponse(content=response.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
        
            if redis_client.exists(f"lock_user:{user.id}"):
                response = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Login Failed !!! User is locked")
                return JSONResponse(content=response.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            
            if not check_password(data.password, user.password_hash):
                attempts = redis_client.incr(f"login_attempts:{user.id}")
                redis_client.expire(f"login_attempts:{user.id}", 300)
                if attempts >= 3:
                    redis_client.setex(f"lock_user:{user.id}", 120, str(user.id))
                    logger.error("User is locked")
                    redis_client.delete(f"login_attempts:{user.id}")
                    response = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Login Failed ")
                    return JSONResponse(content=response.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
                logger.error("Invalid Credentials")
                response = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Login Failed")
                return JSONResponse(content=response.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            
            redis_client.delete(f"login_attempts:{user.id}")
            session_id = "session_id"+ str(user.id)
            redis_client.setex(
                f"session:{session_id}",
                3600,
                str(user.id)
            )
            response =  JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Login successful"} )   
            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                secure=False,   
                samesite="lax",
                max_age=3600
            )        
            return response
        except Exception as e:
            logger.error(f"Error logging in: {e}")
            response = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error logging in")
            return JSONResponse(content=response.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) 


@router.post("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "No active session"}
        )

    redis_client.delete(f"session:{session_id}")
    response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Logout successful"})
    response.delete_cookie("session_id")
    return response


@router.post("/forgot/password")
async def reset_password( data: ForgotPasswordRequest, db: Session = Depends(get_db)):
      user = db.query(User).filter(User.email == data.email).first()
      response = {"message": "If an account exists, a password reset link has been sent."}
      if user is None:
          return JSONResponse(status_code=status.HTTP_200_OK, content=response)
      else:
            token = secrets.token_urlsafe(32)

            redis_client.setex(
                f"password_reset:{token}",
                900, 
                user.id
            )
            reset_link = f"http://localhost:8000/api/v1/reset/password/{token}"
            send_password_reset_email(user.email, reset_link)
            return JSONResponse(status_code=status.HTTP_200_OK, content=response)
    

@router.post("/reset/password/{token}")
async def reset_password(token: str, password: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = redis_client.get(f"password_reset:{token}")
    if user_id is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid token"})
    else:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_verified :
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid token"})
        try:
            if not validate_password(password.password):
                content = {
                "message": (
                    "Password is not strong enough. "
                    "Password should be minimum 8 characters. "
                    "Password should contain at least one special character. "
                    "Password should contain one digit and one uppercase letter."
                )
            }
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)
            if check_password(password.password, user.password_hash):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "New password cannot be same as old password"})

            password_hashed =  hash_password(password.password)
            user.password_hash = password_hashed
            db.commit()
            redis_client.delete(f"password_reset:{token}")
            redis_client.delete(f"session:session_id{user_id}")
            redis_client.delete(f"otp_{user_id}")
            redis_client.delete(f"password_reset:{token}")
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Password reset successful"})
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error resetting password for user_id={user_id}: {e}")
            return JSONResponse(status_code=500, content={"message": "Internal server error"})

        except Exception as e:
            logger.error(f"Unexpected error resetting password for user_id={user_id}: {e}")
            return JSONResponse(status_code=500, content={"message": "Internal server error"})