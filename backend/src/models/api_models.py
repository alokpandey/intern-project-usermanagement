from pydantic import BaseModel, EmailStr

class UserData(BaseModel):
    username: str
    email: EmailStr 
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SuccessResponse(BaseModel):
    message: str
    user_id: int
    verification_required: bool

class ErrorResponse(BaseModel):
    status_code: int
    message: str

class VerifyOTP(BaseModel):
    user_id: int
    otp: int

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    password: str
