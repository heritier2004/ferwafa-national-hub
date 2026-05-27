from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
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
    institution_name: Optional[str] = None

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    clean_email = user.email.strip()
    db_user = db.query(User).filter(User.email.ilike(clean_email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=clean_email,
        password_hash=hashed_password,
        role=user.role,
        full_name=user.full_name,
        photo_url=user.photo_url
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

import uuid
import os

@router.post("/register_institution", status_code=status.HTTP_201_CREATED)
def register_institution(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    contact: str = Form(...),
    type: str = Form(...),
    province: str = Form(...),
    district: str = Form(...),
    sector: Optional[str] = Form(None),
    village: Optional[str] = Form(None),
    hosting_stadium: Optional[str] = Form(None),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    from backend.app.database.models import Institution
    
    clean_email = email.strip()
    db_user = db.query(User).filter(User.email.ilike(clean_email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    logo_url = None
    if logo:
        # Simulate saving the uploaded file
        ext = os.path.splitext(logo.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        logo_url = f"/uploads/{filename}"
        
    code = f"{type.upper()[:3]}-{uuid.uuid4().hex[:6].upper()}"
    
    new_inst = Institution(
        name=name,
        type=type.lower(),
        code=code,
        contact=contact,
        province=province,
        district=district,
        sector=sector,
        cell=village,
        stadium_name=hosting_stadium,
        logo_url=logo_url,
        status="PENDING",
        is_active=False
    )
    db.add(new_inst)
    db.commit()
    db.refresh(new_inst)
    
    hashed_password = get_password_hash(password)
    new_user = User(
        email=clean_email,
        password_hash=hashed_password,
        role=type.upper(),
        full_name=name,
        institution_id=new_inst.id,
        is_active=False
    )
    db.add(new_user)
    db.commit()
    
    return {"message": "Registration submitted successfully. Waiting for FERWAFA approval."}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Case-insensitive email lookup for Global Standard compliance, aggressively trimming whitespace
    clean_username = form_data.username.strip()
    user = db.query(User).filter(User.email.ilike(clean_username)).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not active. Please wait for FERWAFA approval.",
        )
        
    # Fetch Institution details if applicable
    from backend.app.database.models import Institution
    logo = user.photo_url
    stadium = None
    inst = None
    
    if user.institution_id:
        inst = db.query(Institution).filter(Institution.id == user.institution_id).first()
        if inst:
            if inst.status != "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your registration is currently {inst.status}. Please wait for FERWAFA approval.",
                )
            logo = inst.logo_url
            stadium = inst.stadium_name
    
    access_token = create_access_token(data={
        "sub": user.email, 
        "id": user.id,
        "role": user.role,
        "institution_id": user.institution_id
    })
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role, 
        "full_name": user.full_name,
        "logo_url": logo,
        "stadium_name": stadium,
        "institution_name": inst.name if user.institution_id and inst else user.full_name
    }
