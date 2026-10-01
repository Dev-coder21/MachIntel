from typing import List, Optional
import uuid
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from backend.app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(User.email == email.lower().strip())
        ).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(User.username == username.strip())
        ).scalar_one_or_none()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        ident = identifier.strip().lower()
        return self.db.execute(
            select(User).where(
                or_(
                    User.email == ident,
                    User.username == identifier.strip()
                )
            )
        ).scalar_one_or_none()

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return list(
            self.db.execute(
                select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
            ).scalars().all()
        )

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
