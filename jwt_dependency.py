from fastapi import Header, HTTPException
from auth_utils import decode_token

# ─────────────────────────────────────────────
# CONCEPT: JWT Dependency
# This replaces verify_api_key for protected routes.
# It reads the Bearer token from the Authorization header,
# decodes it, and returns the current user's data.
#
# Usage in any endpoint:
#   def my_endpoint(current_user = Depends(get_current_user)):
#       print(current_user["email"])  # always available
#
# If token is missing or invalid → automatic 401
# If token is valid → endpoint runs with user data
# ─────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    """
    Extract and validate JWT from Authorization header.
    Header format: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    # Header value is "Bearer <token>" — we split and take the token part
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Use: Bearer <token>"
        )

    token = parts[1]
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    # CONCEPT: Token type check
    # Reject refresh tokens used as access tokens
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type"
        )

    return payload