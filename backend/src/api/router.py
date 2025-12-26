from fastapi import APIRouter, Depends,  HTTPException, status
from ..models.api_models import UserData, SuccessResponse, ErrorResponse, VerifyOTP, UserLogin
from ..models.DB_models import User
from ..session import get_db
import logging
from sqlalchemy.orm import Session
from src.utils.hasher import hash_password, check_password
from fastapi.responses import JSONResponse
from src.utils.send_email import send_email_verification
from ..session import redis_client

logger = logging.getLogger(__name__)

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
            email_status=send_email_verification(user.email, new_user.id)
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
            if db.query(User).filter(User.email == data.email).first() is None:
                logger.error("User does not exist")
                respose = ErrorResponse(status_code=status.HTTP_404_NOT_FOUND, message="User does not exist")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_404_NOT_FOUND)
            elif db.query(User).filter(User.email == data.email).first().is_verified == False:
                logger.error("User is not verified")
                respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="User is not verified")
                return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
            else:
                if check_password(data.password, db.query(User).filter(User.email == data.email).first().password_hash):
                    return {"message" : "Login successful"}
                else:
                    logger.error("Invalid Credentials")
                    respose = ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Invalid password")
                    return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Error logging in: {e}")
            respose = ErrorResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Error logging in")
            return JSONResponse(content=respose.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) 


@router.post("/logout")
async def login():
    return {"logout successful"}  