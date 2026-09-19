"""
services.auth_service

Registration creates an Organization AND its first User together -
every user needs a workspace, and Phase 4 has no separate "join an
existing organization" flow yet (that would need invites, which is out
of scope for now - every registration starts a new organization).
"""

from sqlalchemy.orm import Session

from backend.models import Organization, User
from backend.services.security import hash_password, verify_password


class EmailAlreadyRegistered(Exception):
    pass


def register_user(
    db: Session, email: str, password: str, organization_name: str | None
) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise EmailAlreadyRegistered(f"An account with {email} already exists.")

    organization = Organization(name=organization_name or f"{email.split('@')[0]}'s workspace")
    db.add(organization)
    db.flush()  # assigns organization.id without committing yet

    user = User(
        email=email,
        password_hash=hash_password(password),
        organization_id=organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
