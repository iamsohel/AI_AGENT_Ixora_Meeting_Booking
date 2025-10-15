"""Authentication utilities for admin users."""

import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database.models import AdminUser
from database.database import get_db

load_dotenv()

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", message=".*bcrypt.*")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        return payload

    except JWTError:
        raise credentials_exception


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """
    Get the current authenticated admin user.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Authenticated admin user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_token(token)

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    # Get user from database
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()

    return admin


def authenticate_admin(db: Session, username: str, password: str) -> Optional[AdminUser]:
    """
    Authenticate an admin user.

    Args:
        db: Database session
        username: Username
        password: Plain password

    Returns:
        Admin user if authentication successful, None otherwise
    """
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()

    if not admin:
        return None

    if not verify_password(password, admin.hashed_password):
        return None

    if not admin.is_active:
        return None

    return admin


def create_admin_user(
    db: Session,
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    is_superuser: bool = False
) -> AdminUser:
    """
    Create a new admin user.

    Args:
        db: Database session
        username: Username
        password: Plain password
        email: Email address
        full_name: Full name
        is_superuser: Whether user is a superuser

    Returns:
        Created admin user

    Raises:
        ValueError: If username already exists
    """
    # Check if username exists
    existing = db.query(AdminUser).filter(AdminUser.username == username).first()
    if existing:
        raise ValueError(f"Username '{username}' already exists")

    # Check if email exists
    if email:
        existing_email = db.query(AdminUser).filter(AdminUser.email == email).first()
        if existing_email:
            raise ValueError(f"Email '{email}' already exists")

    # Create new admin user
    admin = AdminUser(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_superuser=is_superuser,
        is_active=True
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin
