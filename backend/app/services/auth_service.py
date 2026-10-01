import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.errors import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
)
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.models.user import User, UserRole
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.schemas.user import UserCreate, UserRead


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate(self, login_data: LoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_username_or_email(login_data.username_or_email)
        if not user:
            raise AuthenticationException("Invalid username, email, or password")

        if not verify_password(login_data.password, user.hashed_password):
            raise AuthenticationException("Invalid username, email, or password")

        if not user.is_active:
            raise AuthenticationException("Account has been deactivated")

        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )

    def register(self, user_in: UserCreate) -> UserRead:
        if self.user_repo.get_by_email(user_in.email):
            raise ConflictException(f"User with email '{user_in.email}' already exists")

        if self.user_repo.get_by_username(user_in.username):
            raise ConflictException(f"Username '{user_in.username}' is already taken")

        hashed_pw = hash_password(user_in.password)
        new_user = User(
            email=user_in.email.lower().strip(),
            username=user_in.username.strip(),
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=True,
        )
        created_user = self.user_repo.create(new_user)
        return UserRead.model_validate(created_user)

    def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")
        return user
