from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import List, Optional

class UserCreate(BaseModel):
    email: EmailStr
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
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    seeker_id: int
    status: str
    created_at: Optional[datetime] = None
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    seeker_email: Optional[str] = None

    class Config:
        from_attributes = True

class ExternalJob(BaseModel):
    id: str
    source: str = "adzuna"
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None      # short snippet from Adzuna: render as plain text
    contract_time: Optional[str] = None    # "full_time" / "part_time" / None
    contract_type: Optional[str] = None    # "permanent" / "contract" / None
    category: Optional[str] = None
    created: Optional[str] = None          # ISO timestamp
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_is_predicted: bool = False
    redirect_url: str

class ExternalJobResponse(BaseModel):
    count: int
    page: int
    has_more: bool
    jobs: List[ExternalJob]
    attribution: str = "Jobs by Adzuna"
