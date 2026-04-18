from backend.app.config.database import SessionLocal
from backend.app.database.models import User
from backend.app.auth.security import verify_password, create_access_token

def test_login():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@ferwafa.rw").first()
        if not user:
            print("User NOT found")
            return
        
        print(f"User found: {user.email}")
        # Test password verification
        is_valid = verify_password("ANGEU", user.password_hash)
        print(f"Password Valid: {is_valid}")
        
        # Test token creation
        token = create_access_token(data={"sub": user.email, "role": user.role})
        print(f"Token created: {token[:20]}...")
        print("SUCCESS")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
