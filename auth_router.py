from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from database import get_connection
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

# ─────────────────────────────────────────────
# CONCEPT: APIRouter
# Instead of putting everything in main.py,
# we use APIRouter to group related endpoints.
# This router handles /auth/* endpoints.
# main.py includes it with app.include_router().
# As your app grows, each feature gets its own router:
# auth_router.py, invoice_router.py, product_router.py
# ─────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Pydantic schemas (input validation) ──────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ────────────────────────────────

@router.post("/register")
def register(data: RegisterRequest):
    """
    Create a new user account.
    Steps:
    1. Check if email already exists
    2. Hash the password (NEVER store plain text)
    3. Insert into users table
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check duplicate email
        cursor.execute("SELECT id FROM users WHERE email = %s", (data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(data.password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s)",
            (data.email, hashed, data.full_name),
        )
        conn.commit()
        return {"message": "Account created successfully"}

    finally:
        conn.close()


@router.post("/login")
def login(data: LoginRequest):
    """
    Authenticate user and return tokens.
    Steps:
    1. Find user by email
    2. Verify password against stored hash
    3. Generate access + refresh tokens
    4. Return both tokens

    CONCEPT: Why two tokens?
    - access_token: sent with every API request (short lived = safer)
    - refresh_token: stored securely by client, used ONLY to get
      a new access_token when it expires (long lived = convenient)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = ?", (data.email,))
        user = cursor.fetchone()

        # CONCEPT: Same error for wrong email AND wrong password
        # Never tell attacker which one was wrong —
        # that would help them know if an email exists in your system
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token_data = {"sub": user["email"], "user_id": user["id"]}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    finally:
        conn.close()


@router.post("/refresh")
def refresh(data: RefreshRequest):
    """
    Get a new access token using a refresh token.
    Called automatically by the client when access_token expires.
    User never has to log in again — seamless experience.
    """
    payload = decode_token(data.refresh_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # CONCEPT: Token type check
    # Prevent someone from using an access token as a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Issue a fresh access token
    token_data = {"sub": payload["sub"], "user_id": payload["user_id"]}
    new_access_token = create_access_token(token_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }