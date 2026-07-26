from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class UserCreate(BaseModel):
    email: str
    password: str
    role: str

    @validator('role')
    def role_must_be_valid(cls, v):
        if v not in ['employer', 'seeker']:
            raise ValueError("Role must be 'employer' or 'seeker'")
        return v

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class JobCreate(BaseModel):
    title: str
    description: str
    company: str
    location: str

    @validator('title', 'description', 'company', 'location')
    def must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    company: str
    location: str
    is_open: bool
    employer_id: int

    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    seeker_id: int
    status: str

    class Config:
        from_attributes = True