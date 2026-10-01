import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.base import Base
from backend.app.main import app
from backend.app.models.user import User, UserRole

# Use local test database or session for testing
test_engine = create_engine(settings.DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    # Keep schema intact


@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def create_test_user(db):
    def _create_user(
        username: str = None,
        email: str = None,
        password: str = "securepassword123",
        role: UserRole = UserRole.OPERATOR,
    ) -> User:
        unique_id = uuid.uuid4().hex[:6]
        user = User(
            username=username or f"user_{unique_id}",
            email=email or f"user_{unique_id}@example.com",
            hashed_password=hash_password(password),
            full_name=f"Test User {unique_id}",
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _create_user


@pytest.fixture
def admin_token_headers(create_test_user):
    admin = create_test_user(role=UserRole.ADMIN)
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_token_headers(create_test_user):
    op = create_test_user(role=UserRole.OPERATOR)
    token = create_access_token(subject=str(op.id), role=op.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_token_headers(create_test_user):
    viewer = create_test_user(role=UserRole.VIEWER)
    token = create_access_token(subject=str(viewer.id), role=viewer.role.value)
    return {"Authorization": f"Bearer {token}"}
