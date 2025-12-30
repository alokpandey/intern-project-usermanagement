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


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

router = APIRouter()

postgres_url = "postgresql://admin:admin@localhost:5432/mydb"
special_chars = "#@!%&*"


@router.post("/register")
async def register(user : UserData, db: Session = Depends(get_db)):
    if not user.username  or not user.email or not user.password or user.email.endswith("@gmail.com") == False or not user.username.isalpha():
        logger.error("Invalid input")
        respose = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)    

    elif ( len(user.password) < 8 or not any(char in special_chars for char in user.password) or not any(char.isdigit() for char in user.password) or not any(char.isupper() for char in user.password)): 
        logger.error("PASSWORD NOT STRONG!!!")
        respose = ErrorResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, message=f""" * Password should be minimum 8 characters.
                                * Password should contain atleast one special character.  
                                * Password should contaian One digit, and one uppercase letter.""")
        return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_406_NOT_ACCEPTABLE)
    
    elif db.query(User).filter(User.email == user.email).first() or db.query(User).filter(User.username == user.username).first():
        logger.error("User already exists")
        respose = ErrorResponse(status_code=status.HTTP_409_CONFLICT, message="User already exists")
        return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_409_CONFLICT)
    
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
                respose = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error sending email")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error adding user to database: {e}")
            respose = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error adding user to database")
            return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    respose=SuccessResponse(message="User registered successfully. Please verify your email.", user_id=new_user.id, verification_required=True)
    return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_201_CREATED)


@router.post("/verify/otp")
async def login(data : VerifyOTP, db: Session = Depends(get_db)):
    if data.user_id == "" or data.otp == "":
        logger.error("Invalid input")
        respose = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            otp = redis_client.get(f"otp_{data.user_id}")
            if otp is None:
                logger.error("OTP expired")
                respose = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="OTP expired")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
            else:
                if int(otp) == data.otp:
                    redis_client.delete(f"otp_{data.user_id}")
                    db.query(User).filter(User.id == data.user_id).update({"is_verified": True})
                    db.commit()
                    return {"message" : "OTP verified successfully"}
                else:
                    logger.error("Invalid OTP")
                    respose = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid OTP")
                    return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            respose = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error verifying OTP")
            return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
async def login(data : UserLogin, db: Session = Depends(get_db)):
    if data.email == "" or data.password == "":
        logger.error("Invalid input")
        respose = ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid input")
        return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
    else:
        try: 
            user = db.query(User).filter(User.email == data.email).first()
            if not user:
                logger.error("User does not exist")
                respose = ErrorResponse(status_code=status.HTTP_404_NOT_FOUND, message="User does not exist")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_404_NOT_FOUND)
            if not user.is_verified:
                logger.error("User is not verified")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="User is not verified")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            if not user.is_active:
                logger.error("User is not active")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="User is not active")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            is_locked = redis_client.get(f"lock_user:{user.id}")
            if is_locked:
                logger.error("User is locked")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="User is locked")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            if user.failed_login_attempts >= 3:
                logger.error("User is locked")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="User is locked")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            if not check_password(data.password, user.password_hash):
                user.failed_login_attempts += 1
                db.commit()
                logger.error("Invalid Credentials")
                if user.failed_login_attempts >= 3:
                    redis_client.setex(f"lock_user:{user.id}", 120, str(user.id))
                    user.failed_login_attempts = 0
                db.commit()
                logger.error("User is locked")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Invalid Credentials")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            
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
            user.failed_login_attempts = 0 
            db.commit()
            logger.info("Login successful")
            return response
        except Exception as e:
            logger.error(f"Error logging in: {e}")
            respose = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error logging in")
            return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) 


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
        if not user:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid token"})
        try:
            if (len(password.password) < 8 or not any(char in special_chars for char in password.password) or not any(char.isdigit() for char in password.password) or not any(char.isupper() for char in password.password)):
                content = {"message": "Password is not strong enough"
                "* Password should be minimum 8 characters."
                "* Password should contain atleast one special character.  "
                "* Password should contaian One digit, and one uppercase letter."}
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)
            elif hash_password(password.password) == user.password_hash:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "New password cannot be same as old password"})
            else:
                password_hashed =  hash_password(password.password)
                user.password_hash = password_hashed
                db.commit()
            redis_client.delete(f"password_reset:{token}")
            redis_client.delete(f"session:session_id{user_id}")
            redis_client.delete(f"otp_{user_id}")
            redis_client.delete(f"password_reset:{token}")
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Password reset successful"})
        except Exception as e:
            print(e)
