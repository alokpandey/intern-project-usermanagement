from typing import Optional
from pydantic import BaseModel, Field
# from pydantic import EmailStr

class UserCreate(BaseModel):
    email: str
    username: str
    password: str 

class UserLoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str
