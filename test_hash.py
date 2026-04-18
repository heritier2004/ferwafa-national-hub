from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
try:
    h = pwd_context.hash("ANGEU")
    print(f"Hash: {h}")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
