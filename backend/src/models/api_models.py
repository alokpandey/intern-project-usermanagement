from pydantic import BaseModel


class UserData(BaseModel):
    username: str
    email: str 
    password: str

class UserLogin(BaseModel):
    email: str 
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
