from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, require_roles
from backend.app.models.user import User, UserRole
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserRead

router = APIRouter(
    prefix="/admin",
    tags=["Administration & RBAC"],
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)


@router.get("/users", response_model=List[UserRead], summary="List registered users (Admin only)")
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[UserRead]:
    """Retrieve user registry with pagination. Restricted to ADMIN role."""
    repo = UserRepository(db)
    users = repo.list_users(skip=skip, limit=limit)
    return [UserRead.model_validate(u) for u in users]
