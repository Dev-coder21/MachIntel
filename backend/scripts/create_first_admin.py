#!/usr/bin/env python3
"""
Safe administrative bootstrap script for MachIntel.
Creates the initial system administrator account without committing hard-coded credentials.
Credentials can be passed via environment variables (ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD)
or entered interactively.
"""
import os
import sys
import getpass

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.repositories.user_repository import UserRepository


def create_admin():
    email = os.getenv("ADMIN_EMAIL")
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not email:
        email = input("Enter admin email: ").strip()
    if not username:
        username = input("Enter admin username: ").strip()
    if not password:
        password = getpass.getpass("Enter admin password (min 8 characters): ").strip()

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.get_by_email(email):
            print(f"Info: User with email '{email}' already exists. Skipping creation.")
            return

        if repo.get_by_username(username):
            print(f"Info: User with username '{username}' already exists. Skipping creation.")
            return

        admin_user = User(
            email=email.lower().strip(),
            username=username.strip(),
            hashed_password=hash_password(password),
            full_name="MachIntel System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        repo.create(admin_user)
        print(f"Success: Admin account '{username}' ({email}) created successfully with role ADMIN.")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
