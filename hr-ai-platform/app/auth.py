"""JWT authentication and authorization utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its hash."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, role: str) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    """Decode and verify a JWT. Returns the payload dict or raises."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserModel:
    """Extract and return the current authenticated user.

    Raises 401 if the token is missing, invalid, or the user doesn't exist.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = verify_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — access token required",
        )

    user_id = payload.get("sub")
    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=user_id, is_active=True).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )
        return user
    finally:
        session.close()


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserModel]:
    """Return the current user if a valid token is present, else None.

    Used for endpoints that work with or without auth (e.g. /chat backward compat).
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


class RoleChecker:
    """Dependency that enforces one or more allowed roles."""

    def __init__(self, *allowed_roles: str):
        self.allowed_roles = set(allowed_roles)

    def __call__(self, user: UserModel = Depends(get_current_user)) -> UserModel:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized. Required: {', '.join(self.allowed_roles)}",
            )
        return user


# Convenience instances
require_hr = RoleChecker("hr", "higher_authority")
require_authority = RoleChecker("higher_authority")
