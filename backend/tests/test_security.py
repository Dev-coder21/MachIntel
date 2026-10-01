import pytest
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    raw_password = "SuperIndustrialSecret987!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_access_token_creation_and_decoding():
    subject = "user_42"
    role = "ADMIN"
    token = create_access_token(subject=subject, role=role)

    decoded = decode_access_token(token)
    assert decoded["sub"] == subject
    assert decoded["role"] == role
    assert "exp" in decoded
    assert "iat" in decoded
