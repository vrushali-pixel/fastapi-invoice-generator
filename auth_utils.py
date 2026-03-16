from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONCEPT: Password hashing
# pwd_context is our hashing engine.
# bcrypt is the algorithm — it's slow ON PURPOSE.
# Slow = harder for attackers to brute force.
# hash()   → converts plain password to hash
# verify() → checks plain password against hash
# ─────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─────────────────────────────────────────────
# CONCEPT: JWT Secret Key
# This is the key used to SIGN tokens.
# Anyone with this key can create valid tokens.
# So it must never be committed to GitHub.
# We read it from .env — same pattern as API_KEY.
# ─────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-change-this")
ALGORITHM = "HS256"  # HMAC with SHA-256 — industry standard

# Token expiry times
ACCESS_TOKEN_EXPIRE_MINUTES = 30   # short lived — limits damage if leaked
REFRESH_TOKEN_EXPIRE_DAYS = 7      # long lived — so user stays logged in


def hash_password(plain_password: str) -> str:
    """
    Convert plain text password to bcrypt hash.
    Called once at registration.
    Example:
        hash_password("mypassword") 
        → "$2b$12$xK9Lk3mN..."
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if plain password matches the stored hash.
    Called at login.
    Example:
        verify_password("mypassword", "$2b$12$xK9Lk3mN...") → True
        verify_password("wrongpass",  "$2b$12$xK9Lk3mN...") → False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Create a short-lived JWT access token.
    'data' contains the user info to embed — typically {"sub": user_email}.
    'sub' stands for 'subject' — it's a JWT standard field name.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a long-lived JWT refresh token.
    Same structure as access token but:
    - Lives longer (7 days vs 30 min)
    - Tagged as type: refresh so we can reject it
      if someone tries to use it as an access token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    Raises JWTError if:
    - Token is tampered with
    - Token is expired
    - Token signature doesn't match SECRET_KEY
    Returns the payload dict if valid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None