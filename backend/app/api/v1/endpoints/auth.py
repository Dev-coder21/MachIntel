from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.schemas.user import UserCreate, UserRead
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and issue a signed Bearer JWT token."""
    service = AuthService(db)
    return service.authenticate(login_data)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new user identity with hashed password storage."""
    service = AuthService(db)
    return service.register(user_in)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retrieve current authenticated user profile",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Fetch profile and permissions for the authenticated user session."""
    return UserRead.model_validate(current_user)
