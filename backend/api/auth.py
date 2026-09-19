"""
api.auth

    POST /api/auth/register  -> create an organization + its first user
    POST /api/auth/login     -> exchange email/password for a bearer token
    GET  /api/auth/me        -> the current user, from the bearer token

Login uses OAuth2PasswordRequestForm (form-encoded username/password,
where "username" is the email) rather than a JSON body - this is the
standard FastAPI pattern and is what makes the auto-generated docs'
"Authorize" button work out of the box.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import User
from backend.schemas.auth import RegisterRequest, TokenResponse, UserOut
from backend.services.auth_service import EmailAlreadyRegistered, authenticate_user, register_user
from backend.services.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(
            db,
            email=payload.email,
            password=payload.password,
            organization_name=payload.organization_name,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
