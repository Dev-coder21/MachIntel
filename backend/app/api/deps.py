from typing import Generator, List
import uuid
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationException, PermissionDeniedException
from backend.app.core.security import decode_access_token
from backend.app.db.session import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.repositories.user_repository import UserRepository

# HTTPBearer authorization header scheme
security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides an isolated database session per request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency verifying the JWT Bearer token and resolving the current User."""
    if not auth or not auth.credentials:
        raise AuthenticationException(
            message="Missing authentication credentials",
            details={"scheme": "Bearer"},
        )

    token = auth.credentials
    return _resolve_user_from_token(token, db)


def get_current_user_with_query_token(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    token_query: str = None,
    db: Session = Depends(get_db),
) -> User:
    """Dependency verifying the JWT Bearer token from header OR query param for media endpoints."""
    token = None
    if auth and auth.credentials:
        token = auth.credentials
    elif token_query:
        token = token_query

    if not token:
        raise AuthenticationException(
            message="Missing authentication credentials",
            details={"scheme": "Bearer or token query parameter"},
        )
    return _resolve_user_from_token(token, db)


def _resolve_user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationException("Token payload missing subject identifier")
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise AuthenticationException("Invalid or expired authentication token")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise AuthenticationException("Authenticated user no longer exists")

    if not user.is_active:
        raise AuthenticationException("User account is inactive")

    return user


def require_roles(allowed_roles: List[UserRole]):
    """Factory dependency enforcing Role-Based Access Control (RBAC)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedException(
                message=f"Action requires one of roles: {[r.value for r in allowed_roles]}",
                details={
                    "user_role": current_user.role.value,
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
        return current_user
    return role_checker
