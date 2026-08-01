from argon2 import PasswordHasher
from jose import jwt
from app.core.config import settings

ph = PasswordHasher()
DUMMY_PASSWORD_HASH = ph.hash("dummy-password")

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    try:
        return ph.verify(hash, password)
    except Exception:
        return False


#encode and decode access token
def create_access_token(data: dict) -> str:
    return jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])