from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import User
from backend.app.auth.security import verify_password, create_access_token, get_password_hash
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str   # SUPER_ADMIN | FERWAFA | CLUB | SCHOOL | ACADEMY | SCOUT | ANALYST
    full_name: str
    photo_url: str = None

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    logo_url: Optional[str] = None
    stadium_name: Optional[str] = None

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        full_name=user.full_name,
        photo_url=user.photo_url
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    # Fetch Institution details if applicable
    from backend.app.database.models import Institution
    logo = user.photo_url
    stadium = None
    
    if user.institution_id:
        inst = db.query(Institution).filter(Institution.id == user.institution_id).first()
        if inst:
            logo = inst.logo_url
            stadium = inst.stadium_name
            
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role, 
        "full_name": user.full_name,
        "logo_url": logo,
        "stadium_name": stadium
    }
