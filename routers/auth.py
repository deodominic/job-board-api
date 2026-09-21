from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import User
from schemas import UserCreate, UserResponse, UserLogin, Token
from security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth",tags=["Auth"])

@router.post("/register",status_code=status.HTTP_201_CREATED,response_model=UserResponse)
def register(user: UserCreate,db: Session = Depends(get_db)):
    if user.role not in ["employer","seeker"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be either 'employer' or 'seeker'"
        )
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    hashed = hash_password(user.password)
    new_user = User(email=user.email,password=hashed,role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
@router.post("/login",response_model=Token)
def login(user: UserLogin,db: Session=Depends(get_db)):
    db_user=db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=401, detail="Invalid Credentials"
        )
    if not verify_password(user.password,db_user.password):
        raise HTTPException(status_code=401,detail="Invalid Credentials")
    token = create_access_token({
        "user_id":db_user.id,
        "role":db_user.role
    })
    return {"access_token":token,"token_type":"bearer"}