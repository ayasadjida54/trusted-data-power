"""
api.deps

Shared FastAPI dependencies for the API layer. get_current_user reads
the "Authorization: Bearer <token>" header, verifies and decodes it,
and loads the corresponding User - every protected route depends on
this instead of the Phase 1 hardcoded dev user.
"""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models import User
from backend.services.security import decode_access_token

# tokenUrl is only used to populate FastAPI's auto-generated docs (the
# "Authorize" button) - it doesn't affect how tokens are validated here.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_error

    return user
