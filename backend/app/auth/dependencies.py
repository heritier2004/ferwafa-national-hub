from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from backend.app.auth.security import SECRET_KEY, ALGORITHM
from backend.app.config.database import get_db
import sqlalchemy.orm as orm
from typing import List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: orm.Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        from backend.app.database.models import User
        user = db.query(User).filter(User.id == payload.get("id"), User.is_deleted == False).first()
        if user is None or not user.is_active:
            raise credentials_exception

        return {
            "id": payload.get("id"),
            "username": username, 
            "role": payload.get("role"),
            "institution_id": payload.get("institution_id")
        }
    except JWTError:
        raise credentials_exception


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        # SUPER_ADMIN has global authority over all modules
        if user["role"] == "SUPER_ADMIN":
            return user
            
        if user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"NATIONAL SECURITY ALERT: {user['role']} attempted unauthorized access to {self.allowed_roles} restricted infrastructure."
            )
        return user
