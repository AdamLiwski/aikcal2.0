import os
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

# --- Konfiguracja Bezpieczeństwa ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_development_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # Token ważny przez 7 dni

# --- Kontekst Hasła ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikuje, czy hasło jawne pasuje do hasła zahashowanego."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Zwraca hash dla podanego hasła."""
    return pwd_context.hash(password)

# --- Tokeny JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tworzy nowy token dostępu JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
