"""
services.security

Password hashing (bcrypt, used directly rather than through passlib -
passlib's bcrypt backend has known version-compatibility issues with
recent bcrypt releases) and JWT access tokens (PyJWT).

SECRET_KEY must be set via environment variable in any real deployment.
The fallback here is for local development only and is not a secret -
it's checked into this repo, so it provides zero security if used
anywhere real. Phase 4 scope is email/password auth with a signed
bearer token; refresh tokens, password reset, and email verification
are explicitly out of scope for now.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash (shouldn't happen for hashes we generated ourselves).
        return False


def create_access_token(subject: str) -> str:
    """`subject` is the value stored in the token's "sub" claim - here,
    the user's id as a string."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (or a subclass) on an invalid/expired token -
    callers are expected to catch that and respond with 401."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
